"""Insurance CRUD-Endpoints."""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.enums import INTERVALS_PER_YEAR
from app.models.models import Insurance, Product
from app.schemas.schemas import InsuranceCreate, InsuranceRead
from app.services import embedding_service

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[InsuranceRead])
def list_all(db: Session = Depends(get_db)) -> list[Insurance]:
    return db.query(Insurance).order_by(Insurance.end_date.is_(None), Insurance.end_date).all()


@router.post("", response_model=InsuranceRead, status_code=status.HTTP_201_CREATED)
def create(payload: InsuranceCreate, db: Session = Depends(get_db)) -> Insurance:
    obj = Insurance(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/summary/financial")
def financial_summary(db: Session = Depends(get_db)) -> dict:
    """Aggregiert Kosten pro Monat und pro Kategorie."""
    rows = db.query(Insurance).all()
    total_year = 0.0
    by_kat: dict[str, float] = {}
    for r in rows:
        if r.praemie_eur is None:
            continue
        # praemie_eur ist Wert pro Zahlungsintervall — also p.a. = praemie * intervals
        per_year = r.praemie_eur * INTERVALS_PER_YEAR.get(r.zahlungsintervall, 1)
        total_year += per_year
        by_kat[r.kategorie.value] = by_kat.get(r.kategorie.value, 0.0) + per_year
    return {
        "total_year_eur": round(total_year, 2),
        "total_month_eur": round(total_year / 12, 2),
        "by_category": {k: round(v, 2) for k, v in sorted(by_kat.items())},
    }


@router.get("/{insurance_id}", response_model=InsuranceRead)
def get_one(insurance_id: int, db: Session = Depends(get_db)) -> Insurance:
    obj = db.get(Insurance, insurance_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")
    return obj


@router.put("/{insurance_id}", response_model=InsuranceRead)
def update(insurance_id: int, payload: InsuranceCreate, db: Session = Depends(get_db)) -> Insurance:
    obj = db.get(Insurance, insurance_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{insurance_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(insurance_id: int, db: Session = Depends(get_db)) -> None:
    obj = db.get(Insurance, insurance_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")

    # Dateien und RAG-Embeddings der zugehörigen Dokumente mit entfernen,
    # sonst bleiben gelöschte Verträge im Chat (Vektorindex) abrufbar.
    base = settings.documents_dir.resolve()
    for doc in obj.documents:
        try:
            path = Path(doc.stored_path).resolve()
            if path.is_relative_to(base):
                path.unlink(missing_ok=True)
        except OSError as e:
            log.warning("Dokumentdatei konnte nicht gelöscht werden (doc=%d): %s", doc.id, e)
        try:
            embedding_service.delete_for_document(doc.id)
        except Exception as e:  # noqa: BLE001
            log.warning("Embeddings konnten nicht gelöscht werden (doc=%d): %s", doc.id, e)

    # Produkt-Verknüpfungen lösen (SQLite erzwingt den FK nicht)
    db.query(Product).filter(Product.linked_insurance_id == insurance_id).update(
        {Product.linked_insurance_id: None}
    )
    db.delete(obj)
    db.commit()
