"""Tests für das automatische Komplett-Backup, den WAL-Checkpoint und die Lösch-Reihenfolge."""
from __future__ import annotations

import shutil
import sqlite3
import zipfile
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import settings
from app.main import app
from app.models.database import checkpoint_wal, init_db
from app.scheduler import notification_job
from app.services import backup_service, storage_service

client = TestClient(app)
_PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100


@pytest.fixture(scope="module", autouse=True)
def _setup_db() -> None:
    init_db()


@pytest.fixture(autouse=True)
def _empty_backup_dir() -> None:
    shutil.rmtree(settings.backup_dir, ignore_errors=True)
    backup_service._last_error = backup_service._last_error_at = None


def _product_with_invoice(name: str) -> tuple[int, int]:
    product_id = client.post(
        "/api/products", json={"name": name, "kategorie": "Elektronik", "purchase_date": "2026-01-01"}
    ).json()["id"]
    r = client.post(
        "/api/invoices",
        data={"product_id": product_id, "purchase_date": "2026-01-01"},
        files={"file": ("beleg.png", _PNG, "image/png")},
    )
    assert r.status_code == 201
    return product_id, r.json()["id"]


def _invoice_path(invoice_id: int) -> Path:
    with closing(sqlite3.connect(settings.db_path)) as con:
        row = con.execute("SELECT stored_path FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
    path = storage_service.resolve_stored_path(row[0], settings.invoices_dir)
    assert path is not None
    return path


def test_auto_backup_contains_database_and_invoices() -> None:
    product_id, invoice_id = _product_with_invoice("Backup-Kamera")
    invoice_file = _invoice_path(invoice_id)

    path = backup_service.create_auto_backup()

    assert path.parent == settings.backup_dir
    assert backup_service._AUTO_BACKUP_RE.match(path.name)
    assert not list(settings.backup_dir.glob("*.tmp"))
    with zipfile.ZipFile(path) as zf:
        names = zf.namelist()
        assert zf.read("db/insurance.sqlite")[:16] == b"SQLite format 3\x00"
        rel = invoice_file.relative_to(settings.invoices_dir.resolve()).as_posix()
        assert f"invoices/{rel}" in names
        assert zf.read(f"invoices/{rel}") == _PNG
        assert "backup-info.json" in names

    status = backup_service.backup_status()
    assert status["count"] == 1
    assert status["last_backup_at"] is not None
    assert status["last_error"] is None
    assert client.get("/api/exports/backup/status").json()["count"] == 1
    assert not backup_service.auto_backup_due()

    client.delete(f"/api/products/{product_id}")


def test_failed_backup_leaves_no_archive_and_is_reported(mocker) -> None:
    mocker.patch.object(backup_service, "write_backup_zip", side_effect=OSError("Datenträger voll"))

    with pytest.raises(OSError):
        backup_service.create_auto_backup()

    assert not list(settings.backup_dir.glob("*"))
    status = backup_service.backup_status()
    assert status["count"] == 0
    assert "Datenträger voll" in status["last_error"]
    assert backup_service.auto_backup_due()


async def test_run_auto_backup_pushes_on_failure(mocker) -> None:
    mocker.patch.object(backup_service, "create_auto_backup", side_effect=OSError("Permission denied"))
    push = mocker.patch.object(notification_job, "notify_failure", new=mocker.AsyncMock())

    await notification_job.run_auto_backup()

    push.assert_awaited_once()
    assert "Permission denied" in push.await_args.args[1]


async def test_run_auto_backup_catchup_skips_when_recent(mocker) -> None:
    backup_service.create_auto_backup()
    create = mocker.patch.object(backup_service, "create_auto_backup")

    await notification_job.run_auto_backup(only_if_due=True)

    create.assert_not_called()


def test_rotation_keeps_seven_days_and_twelve_months() -> None:
    now = datetime(2026, 9, 29, 3, 30)
    # Täglich ein Backup über 500 Tage, am letzten Tag zusätzlich ein zweites
    backups = [(now - timedelta(days=i), Path(f"b{i}.zip")) for i in range(500)]
    backups.insert(0, (now + timedelta(hours=1), Path("extra.zip")))

    deleted = set(backup_service.select_for_deletion(backups))
    kept = [(ts, f) for ts, f in backups if f not in deleted]

    # 7 Tage (je jüngstes) + ältere Monatsenden, insgesamt 12 Monate
    kept_days = {ts.date() for ts, _ in kept if now - ts < timedelta(days=7)}
    assert len(kept_days) == 7
    assert len({(ts.year, ts.month) for ts, _ in kept}) == 12
    assert Path("b0.zip") in deleted  # am selben Tag gibt es ein jüngeres Backup
    assert Path("extra.zip") not in deleted
    assert len(kept) == 7 + 11  # der aktuelle Monat ist in den 7 Tagen enthalten


def test_checkpoint_wal_updates_main_database_file(tmp_path) -> None:
    """Die Hauptdatei insurance.sqlite muss nach dem Checkpoint allein vollständig sein."""
    product_id = client.post("/api/products", json={"name": "WAL-Test", "kategorie": "Test"}).json()["id"]

    checkpoint_wal()

    copy = tmp_path / "main_only.sqlite"
    shutil.copy(settings.db_path, copy)  # ohne -wal-Datei
    with closing(sqlite3.connect(copy)) as con:
        assert con.execute("SELECT count(*) FROM products WHERE id = ?", (product_id,)).fetchone()[0] == 1

    client.delete(f"/api/products/{product_id}")


def test_invoice_file_kept_when_delete_commit_fails(mocker) -> None:
    """Scheitert der Commit, darf die Beleg-Datei nicht schon gelöscht sein."""
    product_id, invoice_id = _product_with_invoice("Commit-Fehler-Test")
    invoice_file = _invoice_path(invoice_id)

    mocker.patch.object(Session, "commit", side_effect=RuntimeError("database is locked"))
    failing_client = TestClient(app, raise_server_exceptions=False)
    r = failing_client.delete(f"/api/invoices/{invoice_id}?force=true")
    assert r.status_code == 500
    mocker.stopall()

    assert invoice_file.exists()
    assert client.get(f"/api/invoices/{invoice_id}").status_code == 200

    r = client.delete(f"/api/invoices/{invoice_id}?force=true")
    assert r.status_code == 204
    assert not invoice_file.exists()
    client.delete(f"/api/products/{product_id}")
