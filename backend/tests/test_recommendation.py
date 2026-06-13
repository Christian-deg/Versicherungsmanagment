"""Tests für recommendation_service: Summary, Upsert, jährliche Auffrischung.

Der KI-Aufruf (evaluate) wird gemockt — keine echten OpenAI-Calls.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from app.models.database import SessionLocal, init_db
from app.models.enums import Kategorie, Zahlungsintervall
from app.models.models import Insurance, Recommendation
from app.services import recommendation_service


@pytest.fixture(autouse=True)
def _db() -> None:
    init_db()


def _make_insurance(db) -> Insurance:
    ins = Insurance(
        name="Test KFZ",
        kategorie=Kategorie.KFZ,
        versicherer="Allianz",
        vertragsnummer="X-1",
        praemie_eur=50,
        zahlungsintervall=Zahlungsintervall.MONATLICH,
    )
    db.add(ins)
    db.commit()
    db.refresh(ins)
    return ins


def _fake_empfehlung() -> SimpleNamespace:
    return SimpleNamespace(
        handlungsbedarf=SimpleNamespace(value="pruefen"),
        hinweis="Test-Hinweis",
        details="Test-Details",
    )


def test_build_summary_contains_id_and_key_data() -> None:
    with SessionLocal() as db:
        ins = _make_insurance(db)
        s = recommendation_service._build_summary(ins)
        assert f"insurance_id: {ins.id}" in s
        assert "Kategorie: KFZ" in s
        # 50 EUR monatlich → 600 EUR p.a.
        assert "Prämie pro Jahr (EUR): 600" in s
        db.delete(ins)
        db.commit()


async def test_generate_upserts() -> None:
    with SessionLocal() as db:
        ins = _make_insurance(db)
        with patch.object(recommendation_service, "evaluate", AsyncMock(return_value=_fake_empfehlung())):
            rec = await recommendation_service.generate_for_insurance(db, ins)
            assert rec.handlungsbedarf == "pruefen"
            assert rec.insurance_id == ins.id
            # Zweiter Aufruf erzeugt KEINE zweite Zeile (Upsert)
            await recommendation_service.generate_for_insurance(db, ins)
            cnt = db.query(Recommendation).filter(Recommendation.insurance_id == ins.id).count()
            assert cnt == 1
        db.delete(ins)
        db.commit()


async def test_refresh_skips_fresh_refreshes_stale() -> None:
    with SessionLocal() as db:
        ins = _make_insurance(db)
        with patch.object(recommendation_service, "evaluate", AsyncMock(return_value=_fake_empfehlung())):
            rec = await recommendation_service.generate_for_insurance(db, ins)
            fresh_ts = rec.created_at

            # frisch → wird beim Refresh übersprungen
            await recommendation_service.refresh_stale(db)
            db.refresh(rec)
            assert rec.created_at == fresh_ts

            # künstlich veralten → wird neu bewertet
            rec.created_at = datetime.now(UTC) - timedelta(days=400)
            db.commit()
            await recommendation_service.refresh_stale(db)
            db.refresh(rec)
            refreshed = recommendation_service._as_aware(rec.created_at)
            assert refreshed > datetime.now(UTC) - timedelta(minutes=5)
        db.delete(ins)
        db.commit()
