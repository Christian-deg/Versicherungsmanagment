"""Regressionstests für den Notification-Scheduler (Vorab-Warnungen).

Deckt insbesondere den Fehler ab, dass die 90/30/7-Tage-Warnungen früher erst am
Ablauftag selbst statt rechtzeitig vorher versendet wurden (trigger_date == Ablauf
statt heute).
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

from app.models.database import SessionLocal, init_db
from app.models.enums import Kategorie, NotificationStatus
from app.models.models import Insurance, Notification, Product
from app.scheduler import notification_job
from app.scheduler.notification_job import (
    _bucket_for,
    _build_pending,
    _send_due,
    next_recurring_date,
)


@pytest.fixture(scope="module", autouse=True)
def _setup_db() -> None:
    init_db()


def _mk_insurance(db, *, days_until: int | None) -> Insurance:
    end = date.today() + timedelta(days=days_until) if days_until is not None else None
    ins = Insurance(
        name="Notif Test",
        kategorie=Kategorie.KFZ,
        versicherer="TestVers",
        vertragsnummer="N-1",
        end_date=end,
    )
    db.add(ins)
    db.commit()
    db.refresh(ins)
    return ins


def _notifs_for(db, ref_type: str, ref_id: int) -> list[Notification]:
    return (
        db.query(Notification)
        .filter(Notification.ref_type == ref_type, Notification.ref_id == ref_id)
        .all()
    )


@pytest.mark.parametrize(
    ("days_until", "expected"),
    [(-1, None), (0, 7), (5, 7), (7, 7), (8, 30), (30, 30), (31, 90), (90, 90), (91, None), (500, None)],
)
def test_bucket_for(days_until: int, expected: int | None) -> None:
    assert _bucket_for(days_until) == expected


def test_warning_is_due_today_not_on_expiry() -> None:
    """Kernregression: die 90-Tage-Vorwarnung muss HEUTE fällig sein, nicht erst am Ablauftag."""
    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=90)
        _build_pending(db)
        notifs = _notifs_for(db, "insurance", ins.id)
        assert len(notifs) == 1
        n = notifs[0]
        assert n.days_before == 90
        assert n.trigger_date == date.today()  # nicht == end_date (das war der Bug)
        assert n.trigger_date <= date.today()  # → _send_due versendet noch heute
        assert "in 90 Tagen" in n.message


def test_no_notification_beyond_horizon() -> None:
    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=120)
        _build_pending(db)
        assert _notifs_for(db, "insurance", ins.id) == []


def test_no_notification_for_expired() -> None:
    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=-5)
        _build_pending(db)
        assert _notifs_for(db, "insurance", ins.id) == []


def test_single_bucket_no_spam() -> None:
    """Ein in 5 Tagen ablaufender Vertrag erhält genau EINE (7-Tage-)Warnung, nicht drei."""
    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=5)
        _build_pending(db)
        notifs = _notifs_for(db, "insurance", ins.id)
        assert len(notifs) == 1
        assert notifs[0].days_before == 7


def test_dedup_on_repeated_runs() -> None:
    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=30)
        _build_pending(db)
        _build_pending(db)
        assert len(_notifs_for(db, "insurance", ins.id)) == 1


def test_product_warranty_notification() -> None:
    with SessionLocal() as db:
        p = Product(name="Laptop", kategorie="Elektronik", warranty_end=date.today() + timedelta(days=7))
        db.add(p)
        db.commit()
        db.refresh(p)
        _build_pending(db)
        notifs = _notifs_for(db, "product", p.id)
        assert len(notifs) == 1
        assert notifs[0].days_before == 7


def test_archived_product_gets_no_notification() -> None:
    """Archivierte Produkte (verkauft/entsorgt) erzeugen keine Garantie-Warnung mehr."""
    with SessionLocal() as db:
        p = Product(
            name="Verkauftes Gerät",
            kategorie="Elektronik",
            warranty_end=date.today() + timedelta(days=7),
            archived=True,
        )
        db.add(p)
        db.commit()
        db.refresh(p)
        _build_pending(db)
        assert _notifs_for(db, "product", p.id) == []


def test_next_recurring_date() -> None:
    today = date(2026, 7, 2)
    assert next_recurring_date(30, 9, today) == date(2026, 9, 30)  # noch dieses Jahr
    assert next_recurring_date(1, 3, today) == date(2027, 3, 1)  # schon vorbei → nächstes Jahr
    assert next_recurring_date(2, 7, today) == date(2026, 7, 2)  # heute zählt noch
    # 29.02. in Nicht-Schaltjahr → auf Monatsende geklemmt
    assert next_recurring_date(29, 2, date(2026, 1, 1)) == date(2026, 2, 28)


def test_cancellation_deadline_warning() -> None:
    """Kündigungsfristen erzeugen eine eigene Warnung (30/7-Tage-Stufen)."""
    deadline = date.today() + timedelta(days=20)
    with SessionLocal() as db:
        ins = Insurance(
            name="Kuendigung Test",
            kategorie=Kategorie.HAFTPFLICHT,
            versicherer="TestVers",
            vertragsnummer="K-1",
            kuendigung_bis_tag=deadline.day,
            kuendigung_bis_monat=deadline.month,
        )
        db.add(ins)
        db.commit()
        db.refresh(ins)

        _build_pending(db)
        notifs = _notifs_for(db, "insurance_cancellation", ins.id)
        assert len(notifs) == 1
        assert notifs[0].days_before == 30  # 20 Tage → 30er-Stufe
        assert notifs[0].target_date == deadline
        assert "Kündigungsfrist" in notifs[0].message

        # Wiederholter Lauf → keine Doppel-Warnung
        _build_pending(db)
        assert len(_notifs_for(db, "insurance_cancellation", ins.id)) == 1


def test_cancellation_too_far_away_no_warning() -> None:
    """Frist in >30 Tagen → noch keine Warnung."""
    deadline = date.today() + timedelta(days=60)
    with SessionLocal() as db:
        ins = Insurance(
            name="Kuendigung Fern",
            kategorie=Kategorie.HAUSRAT,
            versicherer="TestVers",
            vertragsnummer="K-2",
            kuendigung_bis_tag=deadline.day,
            kuendigung_bis_monat=deadline.month,
        )
        db.add(ins)
        db.commit()
        db.refresh(ins)
        _build_pending(db)
        assert _notifs_for(db, "insurance_cancellation", ins.id) == []


def test_renewed_contract_starts_new_warning_cycle() -> None:
    """Regression: Nach einer Vertragsverlängerung (neues end_date) muss ein neuer
    Warnzyklus starten — früher blockierte die Dedup über (ref, days_before) für immer."""
    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=7)
        _build_pending(db)
        assert len(_notifs_for(db, "insurance", ins.id)) == 1

        # Vertrag verlängert: neues Enddatum in 80 Tagen → neue 90-Tage-Warnung fällig
        ins.end_date = date.today() + timedelta(days=80)
        db.commit()
        _build_pending(db)

        notifs = _notifs_for(db, "insurance", ins.id)
        assert len(notifs) == 2
        new = [n for n in notifs if n.target_date == ins.end_date]
        assert len(new) == 1
        assert new[0].days_before == 90


async def test_stale_pending_notification_is_dropped(mocker) -> None:
    """Wird der Vertrag vor dem Versand verlängert/gelöscht, darf die alte Warnung
    nicht mehr rausgehen — sie wird entfernt."""
    sent: list[str] = []

    async def _fake_push(*, title: str, message: str, priority: int = 0) -> None:
        sent.append(message)

    mocker.patch.object(notification_job, "send_push", _fake_push)

    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=7)
        _build_pending(db)
        # Verlängerung NACH dem Anlegen der Warnung, VOR dem Versand
        ins.end_date = date.today() + timedelta(days=200)
        db.commit()
        await _send_due(db)
        assert _notifs_for(db, "insurance", ins.id) == []

    assert not any(ins.name in m for m in sent if "N-1" in m)


async def test_failed_notification_is_retried(mocker) -> None:
    """Ein vorübergehender Pushover-Ausfall darf eine Warnung nicht dauerhaft verschlucken."""
    from app.services.pushover_service import PushoverError

    async def _failing_push(*, title: str, message: str, priority: int = 0) -> None:
        raise PushoverError("Ausfall simuliert")

    async def _ok_push(*, title: str, message: str, priority: int = 0) -> None:
        pass

    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=7)
        _build_pending(db)

        mocker.patch.object(notification_job, "send_push", _failing_push)
        await _send_due(db)
        notifs = _notifs_for(db, "insurance", ins.id)
        assert notifs[0].status == NotificationStatus.FAILED

        # Nächster Lauf mit funktionierendem Pushover → Warnung wird nachgeholt
        mocker.patch.object(notification_job, "send_push", _ok_push)
        await _send_due(db)
        db.refresh(notifs[0])
        assert notifs[0].status == NotificationStatus.SENT
        assert notifs[0].error is None


async def test_send_due_sends_today_and_marks_sent(mocker) -> None:
    """End-to-End: die erzeugte Warnung wird im selben Lauf versendet und als SENT markiert."""
    sent: list[tuple[str, str, int]] = []

    async def _fake_push(*, title: str, message: str, priority: int = 0) -> None:
        sent.append((title, message, priority))

    mocker.patch.object(notification_job, "send_push", _fake_push)

    with SessionLocal() as db:
        ins = _mk_insurance(db, days_until=7)
        _build_pending(db)
        await _send_due(db)
        notifs = _notifs_for(db, "insurance", ins.id)
        assert len(notifs) == 1
        assert notifs[0].status == NotificationStatus.SENT
        assert notifs[0].sent_at is not None

    # 7-Tage-Frist → Hochpriorität (priority=1)
    assert any(priority == 1 for *_, priority in sent)


async def test_notify_failure_verschluckt_pushover_fehler(mocker) -> None:
    """notify_failure darf nie raisen — auch ohne Pushover-Konfiguration."""
    from app.config import settings
    from app.services import pushover_service

    mocker.patch.object(settings, "pushover_user_key", "")
    mocker.patch.object(settings, "pushover_app_token", "")
    await pushover_service.notify_failure("Titel", "Nachricht")


async def test_embed_task_meldet_fehlschlag_per_push(mocker) -> None:
    """Schlägt das Embedding im Hintergrund fehl, geht eine Störungsmeldung raus."""
    from app.api import documents as documents_api

    mocker.patch.object(
        documents_api.storage_service, "extract_document_text", return_value="Volltext"
    )
    mocker.patch.object(
        documents_api.embedding_service, "embed_and_store", side_effect=RuntimeError("boom")
    )
    pushes: list[str] = []

    async def _fake_notify(title: str, message: str) -> None:
        pushes.append(title)

    mocker.patch.object(documents_api, "notify_failure", _fake_notify)

    # Der fail-safe Hintergrund-Task darf trotz Fehler nicht raisen
    await documents_api._embed_document_task(1, 42, "Metadaten", "C:/ablage/police.pdf")

    assert pushes == ["⚠ Dokument nicht im Suchindex"]
