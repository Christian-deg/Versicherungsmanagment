"""Product CRUD-Endpoints."""
from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.models import Insurance, Invoice, Product
from app.schemas.schemas import ProductCreate, ProductRead

log = logging.getLogger(__name__)
router = APIRouter()


def _validate_linked_insurance(db: Session, payload: ProductCreate) -> None:
    """SQLite erzwingt den FK nicht — Verknüpfung daher explizit prüfen."""
    if payload.linked_insurance_id is not None and not db.get(Insurance, payload.linked_insurance_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verknüpfte Versicherung existiert nicht",
        )


@router.get("", response_model=list[ProductRead])
def list_all(db: Session = Depends(get_db)) -> list[Product]:
    return db.query(Product).order_by(Product.warranty_end.is_(None), Product.warranty_end).all()


@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create(payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    _validate_linked_insurance(db, payload)
    obj = Product(**payload.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/summary/warranty-status")
def warranty_status(db: Session = Depends(get_db)) -> dict:
    """Garantie-Ampel: grün (>90 d), gelb (30-90 d), rot (<30 d), expired.

    Als effektives Enddatum gilt das Maximum aus eigenem warranty_end und
    dem end_date einer verknüpften Versicherung (sofern vorhanden).
    """
    today = date.today()
    rows = db.query(Product).all()
    out = {"green": 0, "yellow": 0, "red": 0, "expired": 0, "no_warranty": 0}
    for r in rows:
        # Effektives Enddatum: eigene Garantie ODER verknüpfte Versicherung
        eff_end = r.warranty_end
        if r.linked_insurance_id:
            ins = db.get(Insurance, r.linked_insurance_id)
            if ins and ins.end_date:
                if eff_end is None or ins.end_date > eff_end:
                    eff_end = ins.end_date

        if not eff_end:
            out["no_warranty"] += 1
            continue
        days = (eff_end - today).days
        if days < 0:
            out["expired"] += 1
        elif days < 30:
            out["red"] += 1
        elif days < 90:
            out["yellow"] += 1
        else:
            out["green"] += 1
    return out


@router.get("/{product_id}", response_model=ProductRead)
def get_one(product_id: int, db: Session = Depends(get_db)) -> Product:
    obj = db.get(Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Produkt nicht gefunden")
    return obj


@router.put("/{product_id}", response_model=ProductRead)
def update(product_id: int, payload: ProductCreate, db: Session = Depends(get_db)) -> Product:
    obj = db.get(Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Produkt nicht gefunden")
    _validate_linked_insurance(db, payload)
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    return obj


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete(product_id: int, db: Session = Depends(get_db)) -> None:
    """Löscht ein Produkt samt aller zugehörigen Rechnungen (inkl. Dateien).

    Explizite Nutzeraktion für den Fall "Produkt wird entsorgt" — die
    Aufbewahrungsfrist einzelner Rechnungen blockiert hier bewusst nicht
    (sie greift nur beim Löschen einzelner Rechnungen über /api/invoices).
    """
    obj = db.get(Product, product_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Produkt nicht gefunden")

    base = settings.invoices_dir.resolve()
    for inv in db.query(Invoice).filter(Invoice.product_id == product_id).all():
        try:
            path = Path(inv.stored_path).resolve()
            if path.is_relative_to(base):
                path.unlink(missing_ok=True)
        except OSError as e:
            log.warning("Rechnungsdatei konnte nicht gelöscht werden (invoice=%d): %s", inv.id, e)
        db.delete(inv)

    db.delete(obj)
    db.commit()
