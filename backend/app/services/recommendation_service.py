"""Erzeugt, speichert und frischt Versicherungs-Empfehlungen auf.

Wird vom Empfehlungs-Endpoint (on demand) und vom Scheduler (jährliche
Auffrischung) gemeinsam genutzt.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy.orm import Session

from app.agents.recommendation_agent import evaluate
from app.models.enums import INTERVALS_PER_YEAR
from app.models.models import Insurance, Recommendation

log = logging.getLogger(__name__)

# Empfehlungen, die älter sind, werden bei der Auffrischung neu bewertet
REFRESH_AFTER_DAYS = 365


def _as_aware(dt: datetime | None) -> datetime | None:
    """Normalisiert einen evtl. naiven SQLite-Timestamp auf UTC-aware."""
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def _build_summary(ins: Insurance) -> str:
    """Baut die strukturierte Zusammenfassung (inkl. insurance_id für das Detail-Tool)."""
    per_year = (
        ins.praemie_eur * INTERVALS_PER_YEAR.get(ins.zahlungsintervall, 1)
        if ins.praemie_eur is not None
        else None
    )
    kuendigung = "nicht angegeben"
    if ins.kuendigung_bis_tag and ins.kuendigung_bis_monat:
        kuendigung = f"kündbar bis {ins.kuendigung_bis_tag:02d}.{ins.kuendigung_bis_monat:02d}."
        if ins.kuendigung_zum_tag and ins.kuendigung_zum_monat:
            kuendigung += f", endet zum {ins.kuendigung_zum_tag:02d}.{ins.kuendigung_zum_monat:02d}."
    return (
        f"insurance_id: {ins.id}\n"
        f"Kategorie: {ins.kategorie.value}\n"
        f"Versicherer: {ins.versicherer}\n"
        f"Laufzeit: {ins.start_date} bis {ins.end_date}\n"
        f"Zahlungsintervall: {ins.zahlungsintervall.value}\n"
        f"Prämie pro Jahr (EUR): {per_year if per_year is not None else 'unbekannt'}\n"
        f"Kündigung: {kuendigung}\n"
        f"Notizen: {ins.notes or '-'}\n"
    )


async def generate_for_insurance(db: Session, ins: Insurance) -> Recommendation:
    """Bewertet eine Versicherung neu (KI) und speichert das Ergebnis (Upsert)."""
    result = await evaluate(_build_summary(ins))
    rec = db.query(Recommendation).filter(Recommendation.insurance_id == ins.id).first()
    if rec is None:
        rec = Recommendation(insurance_id=ins.id)
        db.add(rec)
    rec.handlungsbedarf = result.handlungsbedarf.value
    rec.hinweis = result.hinweis
    rec.details = result.details
    rec.created_at = datetime.now(UTC)
    db.commit()
    db.refresh(rec)
    return rec


async def refresh_stale(db: Session) -> int:
    """Frischt Empfehlungen auf, die fehlen oder älter als REFRESH_AFTER_DAYS sind.

    Gibt die Anzahl neu bewerteter Versicherungen zurück.
    """
    cutoff = datetime.now(UTC) - timedelta(days=REFRESH_AFTER_DAYS)
    count = 0
    for ins in db.query(Insurance).all():
        existing = db.query(Recommendation).filter(Recommendation.insurance_id == ins.id).first()
        created = _as_aware(existing.created_at) if existing else None
        if created is not None and created > cutoff:
            continue  # noch aktuell
        try:
            await generate_for_insurance(db, ins)
            count += 1
        except Exception:  # noqa: BLE001
            log.exception("Empfehlungs-Auffrischung fehlgeschlagen (insurance=%d)", ins.id)
    return count
