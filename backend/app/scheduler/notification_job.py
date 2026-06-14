"""APScheduler-Job: prüft täglich Abläufe und triggert Pushover-Notifications."""
from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import SessionLocal
from app.models.enums import NOTIFICATION_TRIGGERS_DAYS, PRIORITY_HIGH_DAYS, NotificationStatus
from app.models.models import Document, Insurance, Notification, Product
from app.services.pushover_service import PushoverError, send_push
from app.services.recommendation_service import refresh_stale

log = logging.getLogger(__name__)
_scheduler: AsyncIOScheduler | None = None

# Temporäre Uploads, die älter als diese Schwelle sind, werden bereinigt
_INCOMING_MAX_AGE_HOURS = 24


def _ensure_notification(
    db: Session,
    ref_type: str,
    ref_id: int,
    days_before: int,
    trigger_date: date,
    message: str,
) -> Notification | None:
    """Legt eine Notification an, falls für (ref_type, ref_id, days_before) noch nicht vorhanden."""
    existing = (
        db.query(Notification)
        .filter(
            Notification.ref_type == ref_type,
            Notification.ref_id == ref_id,
            Notification.days_before == days_before,
        )
        .first()
    )
    if existing:
        return None
    n = Notification(
        ref_type=ref_type,
        ref_id=ref_id,
        days_before=days_before,
        trigger_date=trigger_date,
        message=message,
        status=NotificationStatus.PENDING,
    )
    db.add(n)
    return n


def _bucket_for(days_until: int) -> int | None:
    """Liefert die engste passende Warnstufe (z.B. 90/30/7) für die Resttage, sonst None.

    days_until=50 → 90 (Band 30<d≤90), days_until=5 → 7, days_until=0 → 7 (heute),
    days_until>90 → None (noch zu früh), days_until<0 → None (bereits abgelaufen).
    """
    if days_until < 0:
        return None
    for threshold in sorted(NOTIFICATION_TRIGGERS_DAYS):
        if days_until <= threshold:
            return threshold
    return None


def _days_phrase(days: int) -> str:
    if days <= 0:
        return "heute"
    if days == 1:
        return "morgen"
    return f"in {days} Tagen"


def _build_pending(db: Session) -> None:
    """Erzeugt fehlende Notification-Einträge für alle relevanten Versicherungen/Produkte.

    Jede Versicherung/Garantie wird genau einer Warnstufe (90/30/7 Tage) zugeordnet —
    der engsten, die noch zutrifft. Die Notification ist sofort fällig
    (trigger_date=heute), und die Deduplizierung in _ensure_notification verhindert
    Doppel-Versand. Durch die Band-Logik (statt exaktem Datumsabgleich) geht keine
    Warnung verloren, falls der tägliche Job einmal ausfällt.
    """
    today = date.today()
    horizon = today + timedelta(days=max(NOTIFICATION_TRIGGERS_DAYS))

    # Versicherungen
    for ins in (
        db.query(Insurance)
        .filter(Insurance.end_date.isnot(None), Insurance.end_date >= today, Insurance.end_date <= horizon)
        .all()
    ):
        days_until = (ins.end_date - today).days
        bucket = _bucket_for(days_until)
        if bucket is None:
            continue
        msg = (
            f"Versicherung '{ins.name}' ({ins.versicherer}, {ins.kategorie.value}) "
            f"läuft {_days_phrase(days_until)} ab ({ins.end_date.isoformat()})."
        )
        _ensure_notification(db, "insurance", ins.id, bucket, today, msg)

    # Produkte (Garantie)
    for p in (
        db.query(Product)
        .filter(
            Product.warranty_end.isnot(None),
            Product.warranty_end >= today,
            Product.warranty_end <= horizon,
        )
        .all()
    ):
        days_until = (p.warranty_end - today).days
        bucket = _bucket_for(days_until)
        if bucket is None:
            continue
        msg = (
            f"Garantie für '{p.name}' ({p.kategorie}) "
            f"endet {_days_phrase(days_until)} ({p.warranty_end.isoformat()})."
        )
        _ensure_notification(db, "product", p.id, bucket, today, msg)

    db.commit()


async def _send_due(db: Session) -> None:
    """Sendet alle PENDING-Notifications, deren trigger_date <= heute."""
    today = date.today()
    due = (
        db.query(Notification)
        .filter(
            Notification.status == NotificationStatus.PENDING,
            Notification.trigger_date <= today,
        )
        .all()
    )
    for n in due:
        priority = 1 if n.days_before <= PRIORITY_HIGH_DAYS else 0
        title = "⚠ Versicherung läuft ab" if n.ref_type == "insurance" else "⚠ Garantie endet"
        try:
            await send_push(title=title, message=n.message, priority=priority)
            n.status = NotificationStatus.SENT
            n.sent_at = datetime.now(UTC)
        except PushoverError as e:
            log.error("Pushover-Versand fehlgeschlagen: %s", e)
            n.status = NotificationStatus.FAILED
            n.error = str(e)[:500]
        except Exception as e:  # noqa: BLE001
            log.error("Unerwarteter Fehler beim Notification-Versand (id=%d): %s", n.id, e)
            n.status = NotificationStatus.FAILED
            n.error = str(e)[:500]
    db.commit()


async def run_notification_job() -> None:
    """Täglicher Job: Notifications berechnen + senden + verwaiste Uploads bereinigen."""
    log.info("Notification-Job gestartet")
    _cleanup_orphan_documents()
    _cleanup_incoming()
    if not settings.pushover_user_key or not settings.pushover_app_token:
        log.warning("Pushover nicht konfiguriert — überspringe Versand")
        return
    try:
        with SessionLocal() as db:
            _build_pending(db)
            await _send_due(db)
    except Exception as e:  # noqa: BLE001
        log.error("Notification-Job fehlgeschlagen: %s", e)
    log.info("Notification-Job beendet")


def _cleanup_orphan_documents() -> None:
    """Entfernt unbestätigte Document-Einträge (älter als 24 h) samt Datei.

    Ohne diesen Schritt blieben DB-Zeilen von nie bestätigten Uploads dauerhaft
    stehen, nachdem _cleanup_incoming nur die Datei gelöscht hat.
    """
    cutoff = datetime.now(UTC) - timedelta(hours=_INCOMING_MAX_AGE_HOURS)
    base = settings.documents_dir.resolve()
    try:
        with SessionLocal() as db:
            orphans = (
                db.query(Document)
                .filter(Document.insurance_id.is_(None), Document.uploaded_at < cutoff)
                .all()
            )
            for doc in orphans:
                try:
                    path = Path(doc.stored_path).resolve()
                    if path.is_relative_to(base):
                        path.unlink(missing_ok=True)
                except OSError as e:
                    log.warning("Orphan-Datei konnte nicht gelöscht werden (doc=%d): %s", doc.id, e)
                db.delete(doc)
            if orphans:
                db.commit()
                log.info("Verwaiste Dokument-Einträge bereinigt: %d", len(orphans))
    except Exception as e:  # noqa: BLE001
        log.error("Orphan-Dokument-Cleanup fehlgeschlagen: %s", e)


async def run_recommendation_refresh() -> None:
    """Wöchentlicher Job: frischt Empfehlungen auf, die älter als ein Jahr sind.

    Bewertet nur fehlende oder >365 Tage alte Empfehlungen neu — die meisten Läufe
    tun nichts. Braucht OpenAI; ohne Key scheitern die Einzelbewertungen still.
    """
    if not settings.openai_api_key:
        return
    log.info("Empfehlungs-Auffrischung gestartet")
    try:
        with SessionLocal() as db:
            n = await refresh_stale(db)
        if n:
            log.info("Empfehlungen aufgefrischt: %d", n)
    except Exception as e:  # noqa: BLE001
        log.error("Empfehlungs-Auffrischung fehlgeschlagen: %s", e)
    log.info("Empfehlungs-Auffrischung beendet")


def run_db_backup() -> None:
    """Monatlicher Job: erstellt ein konsistentes SQLite-Backup im DB-Ordner.

    Verwendet die SQLite-eigene Backup-API (kein simples Kopieren) — dadurch ist
    das Backup auch bei laufenden Schreibzugriffen konsistent.
    Alte Backups werden nach 3 Monaten automatisch gelöscht.
    """
    import sqlite3

    db_path = settings.data_dir / "db" / "insurance.sqlite"
    backup_dir = settings.data_dir / "db"
    backup_dir.mkdir(parents=True, exist_ok=True)

    # Pfad-Traversal-Schutz
    if not db_path.resolve().is_relative_to(settings.data_dir.resolve()):
        log.error("Ungültiger DB-Pfad beim Backup — abgebrochen")
        return
    if not db_path.exists():
        log.warning("DB-Datei nicht gefunden, Backup übersprungen")
        return

    timestamp = datetime.now(UTC).strftime("%Y-%m")
    backup_path = backup_dir / f"insurance.backup.{timestamp}.sqlite"

    try:
        src = sqlite3.connect(str(db_path))
        dst = sqlite3.connect(str(backup_path))
        with dst:
            src.backup(dst)
        dst.close()
        src.close()
        log.info("DB-Backup erstellt: %s", backup_path.name)
    except Exception as e:  # noqa: BLE001
        log.error("DB-Backup fehlgeschlagen: %s", e)
        return

    # Backups älter als 3 Monate löschen
    cutoff = datetime.now(UTC).replace(day=1) - timedelta(days=90)
    for f in backup_dir.glob("insurance.backup.*.sqlite"):
        try:
            stem = f.stem  # z.B. "insurance.backup.2026-01"
            parts = stem.split(".")
            year, month = int(parts[2].split("-")[0]), int(parts[2].split("-")[1])
            backup_date = datetime(year, month, 1, tzinfo=UTC)
            if backup_date < cutoff:
                f.unlink()
                log.info("Altes Backup gelöscht: %s", f.name)
        except (ValueError, IndexError, OSError) as e:
            log.warning("Backup-Datei konnte nicht geprüft/gelöscht werden (%s): %s", f.name, e)


def _cleanup_incoming() -> None:
    """Entfernt verwaiste Upload-Dateien aus dem _incoming-Ordner (älter als 24 h)."""
    base = settings.documents_dir.resolve()
    incoming = base / "_incoming"
    # Pfad-Traversal-Schutz: sicherstellen, dass _incoming innerhalb des Daten-Verzeichnisses liegt
    if not incoming.is_relative_to(base):
        log.warning("Ungültiger _incoming-Pfad erkannt – Cleanup übersprungen")
        return
    if not incoming.is_dir():
        return
    cutoff = datetime.now(UTC) - timedelta(hours=_INCOMING_MAX_AGE_HOURS)
    removed = 0
    for f in incoming.iterdir():
        if not f.is_file():
            continue
        # Auch hier sicherstellen, dass die Datei wirklich im _incoming-Ordner liegt
        if not f.resolve().is_relative_to(incoming.resolve()):
            continue
        try:
            mtime = datetime.fromtimestamp(f.stat().st_mtime, tz=UTC)
            if mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError as e:
            log.warning("Konnte _incoming-Datei nicht löschen (%s): %s", f.name, e)
    if removed:
        log.info("_incoming bereinigt: %d verwaiste Datei(en) gelöscht", removed)


def start_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    # Täglich um 08:00 lokaler Zeit
    _scheduler.add_job(run_notification_job, CronTrigger(hour=8, minute=0), id="daily_notifications")
    # Monatlich am 1. um 02:00 UTC — DB-Backup
    _scheduler.add_job(run_db_backup, CronTrigger(day=1, hour=2, minute=0), id="monthly_db_backup")
    # Wöchentlich (Mo 03:00) — Empfehlungen auffrischen, die älter als ein Jahr sind
    _scheduler.add_job(
        run_recommendation_refresh,
        CronTrigger(day_of_week="mon", hour=3, minute=0),
        id="weekly_recommendation_refresh",
    )
    _scheduler.start()
    log.info("APScheduler gestartet (täglich 08:00)")


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
