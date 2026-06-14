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
from app.scheduler.notification_job import _bucket_for, _build_pending, _send_due


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
