"""Insurance CRUD-Endpoints."""
from __future__ import annotations

import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.enums import INTERVALS_PER_YEAR
from app.models.models import Insurance, PremiumHistory, Product
from app.schemas.schemas import InsuranceCreate, InsuranceRead, PremiumHistoryRead
from app.services import embedding_service, storage_service

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[InsuranceRead])
def list_all(db: Session = Depends(get_db)) -> list[Insurance]:
    return db.query(Insurance).order_by(Insurance.end_date.is_(None), Insurance.end_date).all()


def record_premium(db: Session, ins: Insurance) -> None:
    """Hängt den aktuellen Prämienstand an den Verlauf an (ohne Commit)."""
    db.add(
        PremiumHistory(
            insurance_id=ins.id,
            praemie_eur=ins.praemie_eur,
            zahlungsintervall=ins.zahlungsintervall,
        )
    )


@router.post("", response_model=InsuranceRead, status_code=status.HTTP_201_CREATED)
def create(payload: InsuranceCreate, db: Session = Depends(get_db)) -> Insurance:
    obj = Insurance(**payload.model_dump())
    db.add(obj)
    db.flush()
    record_premium(db, obj)  # Startwert für den Prämienverlauf
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/history/premiums", response_model=list[PremiumHistoryRead])
def premium_history(db: Session = Depends(get_db)) -> list[PremiumHistory]:
    """Prämienverlauf aller Versicherungen (älteste zuerst) — für Trend-Anzeigen im Frontend."""
    return db.query(PremiumHistory).order_by(PremiumHistory.insurance_id, PremiumHistory.changed_at).all()


@router.get("/summary/financial")
def financial_summary(db: Session = Depends(get_db)) -> dict:
    """Aggregiert Kosten pro Monat und pro Kategorie."""
    rows = db.query(Insurance).all()
    total_year = 0.0
    by_kat: dict[str, float] = {}
    by_person: dict[str, float] = {}
    for r in rows:
        if r.praemie_eur is None:
            continue
        # praemie_eur ist Wert pro Zahlungsintervall — also p.a. = praemie * intervals
        per_year = r.praemie_eur * INTERVALS_PER_YEAR.get(r.zahlungsintervall, 1)
        total_year += per_year
        by_kat[r.kategorie.value] = by_kat.get(r.kategorie.value, 0.0) + per_year
        person = (r.person or "").strip() or "Ohne Zuordnung"
        by_person[person] = by_person.get(person, 0.0) + per_year
    return {
        "total_year_eur": round(total_year, 2),
        "total_month_eur": round(total_year / 12, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_kat.items())},
        "by_person": {k: round(v, 2) for k, v in sorted(by_person.items())},
    }


@router.get("/{insurance_id}", response_model=InsuranceRead)
def get_one(insurance_id: int, db: Session = Depends(get_db)) -> Insurance:
    obj = db.get(Insurance, insurance_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")
    return obj


@router.put("/{insurance_id}", response_model=InsuranceRead)
def update(
    insurance_id: int,
    payload: InsuranceCreate,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Insurance:
    obj = db.get(Insurance, insurance_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")
    old_praemie, old_intervall = obj.praemie_eur, obj.zahlungsintervall
    changed = False
    for k, v in payload.model_dump().items():
        if getattr(obj, k) != v:
            changed = True
        setattr(obj, k, v)
    # Prämienverlauf fortschreiben, wenn sich Prämie oder Intervall geändert haben
    if obj.praemie_eur != old_praemie or obj.zahlungsintervall != old_intervall:
        record_premium(db, obj)
    db.commit()
    db.refresh(obj)

    # RAG-Metadaten der zugehörigen Dokumente auffrischen, sonst antwortet der
    # Chat weiter mit den alten Prämien/Laufzeiten aus dem Vektorindex.
    # Texte hier (bei offener Session) bauen — der Task läuft nach der Response.
    if changed and obj.documents:
        doc_texts = [
            (d.id, embedding_service.build_insurance_metadata(obj, d.ai_summary))
            for d in obj.documents
        ]
        background.add_task(embedding_service.refresh_insurance_metadata, obj.id, doc_texts)
    return obj


@router.delete("/{insurance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(insurance_id: int, db: Session = Depends(get_db)) -> None:
    obj = db.get(Insurance, insurance_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")

    docs = [(doc.id, doc.stored_path) for doc in obj.documents]

    # Produkt-Verknüpfungen lösen — foreign_keys=ON würde das Löschen sonst am FK scheitern lassen
    db.query(Product).filter(Product.linked_insurance_id == insurance_id).update(
        {Product.linked_insurance_id: None}
    )
    # Prämienverlauf mit entfernen (kein ORM-Cascade definiert)
    db.query(PremiumHistory).filter(PremiumHistory.insurance_id == insurance_id).delete()
    db.delete(obj)
    db.commit()

    # Dateien und RAG-Embeddings erst nach dem Commit entfernen (sonst Einträge ohne
    # Datei bei Commit-Fehler) — ohne diesen Schritt blieben gelöschte Verträge im
    # Chat (Vektorindex) abrufbar.
    for doc_id, stored_path in docs:
        storage_service.delete_stored_file(stored_path, settings.documents_dir)
        try:
            embedding_service.delete_for_document(doc_id)
        except Exception as e:  # noqa: BLE001
            log.warning("Embeddings konnten nicht gelöscht werden (doc=%d): %s", doc_id, e)
