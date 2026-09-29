"""Komplett-Backups: Datenbank, Suchindex, Dokumente und Rechnungen als ZIP.

Gemeinsam genutzt vom Download-Endpoint (Backup per Klick) und vom täglichen
automatischen Backup. Die SQLite-Datenbanken werden über die Backup-API kopiert:
Eine Datei-Kopie von insurance.sqlite allein wäre unvollständig, solange
Änderungen noch in insurance.sqlite-wal liegen.
"""
from __future__ import annotations

import json
import logging
import re
import sqlite3
import tempfile
import threading
import zipfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

from app.config import settings

log = logging.getLogger(__name__)

AUTO_BACKUP_PREFIX = "versicherung-backup-"
_AUTO_BACKUP_RE = re.compile(r"^versicherung-backup-(\d{4}-\d{2}-\d{2}_\d{6})\.zip$")
_TIMESTAMP_FORMAT = "%Y-%m-%d_%H%M%S"

# Aufbewahrung: jüngstes Backup je Tag (letzte 7 Tage mit Backup) plus jüngstes
# Backup je Monat (letzte 12 Monate) — ein Fehler fällt so auch Wochen später
# noch auf, ohne dass der Backup-Ordner unbegrenzt wächst
KEEP_DAILY = 7
KEEP_MONTHLY = 12

# Automatisches Backup gilt als fällig, wenn das letzte älter ist (Nachholen nach Neustart)
AUTO_BACKUP_MAX_AGE = timedelta(hours=20)

_lock = threading.Lock()
_last_error: str | None = None
_last_error_at: datetime | None = None


class BackupError(RuntimeError):
    pass


def _add_sqlite_backup(zf: zipfile.ZipFile, db_path: Path, arcname: str) -> None:
    """Fügt eine konsistente, geprüfte Kopie einer SQLite-DB hinzu (Backup-API statt Datei-Kopie)."""
    if not db_path.exists():
        return
    with tempfile.NamedTemporaryFile(suffix=".sqlite", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with closing(sqlite3.connect(db_path)) as src, closing(sqlite3.connect(tmp_path)) as dst:
            src.backup(dst)
            result = dst.execute("PRAGMA integrity_check").fetchone()[0]
        if result != "ok":
            raise BackupError(f"Integritätsprüfung der Kopie von {db_path.name} fehlgeschlagen: {result}")
        zf.write(tmp_path, arcname)
    finally:
        tmp_path.unlink(missing_ok=True)


def _add_directory(zf: zipfile.ZipFile, base: Path, arcprefix: str) -> int:
    """Fügt alle Dateien eines Verzeichnisses hinzu (ohne temporäre _incoming-Uploads)."""
    if not base.is_dir():
        return 0
    count = 0
    for f in sorted(base.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(base)
        if rel.parts and rel.parts[0] == "_incoming":
            continue
        zf.write(f, f"{arcprefix}/{rel.as_posix()}")
        count += 1
    return count


def write_backup_zip(target: Path) -> dict[str, int]:
    """Schreibt das Komplett-Backup nach target und gibt die Dateianzahl je Ordner zurück.

    PDFs/Bilder sind bereits komprimiert — ZIP_STORED hält das Backup schnell.
    """
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_STORED) as zf:
        _add_sqlite_backup(zf, settings.db_path, "db/insurance.sqlite")
        _add_sqlite_backup(zf, settings.vectordb_dir / "vectors.sqlite", "vectordb/vectors.sqlite")
        counts = {
            "documents": _add_directory(zf, settings.documents_dir.resolve(), "documents"),
            "invoices": _add_directory(zf, settings.invoices_dir.resolve(), "invoices"),
        }
        manifest = {"created_at": datetime.now().isoformat(timespec="seconds"), **counts}
        zf.writestr("backup-info.json", json.dumps(manifest, indent=2))
    return counts


def verify_backup_zip(path: Path) -> None:
    """Liest das Archiv vollständig (CRC-Prüfung) und prüft, dass die Datenbank enthalten ist."""
    with zipfile.ZipFile(path) as zf:
        bad = zf.testzip()
        if bad is not None:
            raise BackupError(f"Backup-Archiv beschädigt (Datei {bad})")
        if "db/insurance.sqlite" not in zf.namelist():
            raise BackupError("Backup-Archiv enthält keine Datenbank")


def list_auto_backups() -> list[tuple[datetime, Path]]:
    """Automatische Backups im Backup-Ordner, neueste zuerst."""
    backup_dir = settings.backup_dir
    if not backup_dir.is_dir():
        return []
    out: list[tuple[datetime, Path]] = []
    for f in backup_dir.glob(f"{AUTO_BACKUP_PREFIX}*.zip"):
        m = _AUTO_BACKUP_RE.match(f.name)
        if not m:
            continue
        try:
            out.append((datetime.strptime(m[1], _TIMESTAMP_FORMAT), f))
        except ValueError:
            continue
    return sorted(out, reverse=True)


def select_for_deletion(backups: list[tuple[datetime, Path]]) -> list[Path]:
    """Backups außerhalb der Aufbewahrung (KEEP_DAILY Tage + KEEP_MONTHLY Monate).

    backups: neueste zuerst (wie von list_auto_backups geliefert).
    """
    keep: set[Path] = set()
    days: set = set()
    months: set = set()
    for ts, f in backups:
        if ts.date() not in days:
            days.add(ts.date())
            if len(days) <= KEEP_DAILY:
                keep.add(f)
        if (ts.year, ts.month) not in months:
            months.add((ts.year, ts.month))
            if len(months) <= KEEP_MONTHLY:
                keep.add(f)
    return [f for _, f in backups if f not in keep]


def auto_backup_due() -> bool:
    backups = list_auto_backups()
    return not backups or datetime.now() - backups[0][0] > AUTO_BACKUP_MAX_AGE


def create_auto_backup() -> Path:
    """Erstellt ein geprüftes Komplett-Backup im Backup-Ordner und räumt alte Backups auf.

    Das Archiv entsteht als .tmp und wird erst nach erfolgreicher Prüfung
    umbenannt — ein abgebrochener Lauf hinterlässt nie ein scheinbar gültiges Backup.
    Wirft bei Fehlern (der Aufrufer meldet sie per Push).
    """
    global _last_error, _last_error_at
    with _lock:
        try:
            backup_dir = settings.backup_dir
            backup_dir.mkdir(parents=True, exist_ok=True)
            final = backup_dir / f"{AUTO_BACKUP_PREFIX}{datetime.now().strftime(_TIMESTAMP_FORMAT)}.zip"
            tmp = final.with_name(final.name + ".tmp")
            try:
                counts = write_backup_zip(tmp)
                verify_backup_zip(tmp)
                tmp.replace(final)
            finally:
                tmp.unlink(missing_ok=True)
        except Exception as e:
            _last_error = str(e)[:300] or type(e).__name__
            _last_error_at = datetime.now()
            raise
        _last_error = _last_error_at = None

    log.info(
        "Automatisches Backup erstellt: %s (%.1f MB, %d Dokumente, %d Rechnungen)",
        final.name,
        final.stat().st_size / (1024 * 1024),
        counts["documents"],
        counts["invoices"],
    )
    for old in select_for_deletion(list_auto_backups()):
        try:
            old.unlink()
            log.info("Altes Backup gelöscht: %s", old.name)
        except OSError as e:
            log.warning("Altes Backup konnte nicht gelöscht werden (%s): %s", old.name, e)
    return final


def backup_status() -> dict:
    """Stand der automatischen Backups für die Oberfläche (ohne Pfade)."""
    backups = list_auto_backups()
    latest = backups[0] if backups else None
    return {
        "count": len(backups),
        "total_mb": round(sum(f.stat().st_size for _, f in backups) / (1024 * 1024), 1),
        "last_backup_at": latest[0].isoformat(timespec="seconds") if latest else None,
        "last_backup_mb": round(latest[1].stat().st_size / (1024 * 1024), 1) if latest else None,
        "last_error": _last_error,
        "last_error_at": _last_error_at.isoformat(timespec="seconds") if _last_error_at else None,
    }
