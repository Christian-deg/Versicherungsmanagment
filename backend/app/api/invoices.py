"""Rechnungs-Upload und -Verwaltung je Produkt."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.agents.invoice_agent import analyze_invoice, analyze_invoice_from_text
from app.config import settings
from app.models.database import get_db
from app.models.models import Invoice, Product
from app.schemas.schemas import InvoiceAnalysisPreview, InvoiceRead
from app.services import storage_service

log = logging.getLogger(__name__)
router = APIRouter()

# Mindest-Aufbewahrungsfrist: 2 Jahre (730 Tage)
MIN_RETENTION_DAYS = 730


def _compute_retain_until(purchase_date: date | None, product: Product) -> date:
    """Aufbewahrungsfrist = max(Kaufdatum + 730 Tage, tatsächliches Garantieende des Produkts).

    Damit werden sowohl 2-jährige als auch 3-jährige (oder längere) Garantien korrekt abgebildet.
    """
    base_date = purchase_date or product.purchase_date or date.today()
    min_retain = base_date + timedelta(days=MIN_RETENTION_DAYS)
    if product.warranty_end and product.warranty_end > min_retain:
        return product.warranty_end
    return min_retain


@router.post("/analyze", response_model=InvoiceAnalysisPreview)
async def analyze_invoice_file(
    file: UploadFile = File(...),
) -> InvoiceAnalysisPreview:
    """Analysiert eine Rechnungsdatei per KI und gibt Kaufdatum, Betrag und Notiz zur
    Prüfung zurück. Der eigentliche Upload erfolgt erst nach Bestätigung.
    """
    import uuid

    content = await file.read(settings.max_invoice_upload_bytes + 1)
    try:
        storage_service.validate_upload(
            file.filename or "rechnung", content, max_bytes=settings.max_invoice_upload_bytes
        )
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Temp-File in _incoming ablegen (innerhalb documents_dir — Pfad-Checks greifen korrekt)
    suffix = Path(file.filename or "rechnung").suffix.lower()
    incoming = settings.documents_dir.resolve() / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    tmp_path = incoming / f"_analyze_{uuid.uuid4().hex}{suffix}"
    tmp_path.write_bytes(content)

    try:
        images = storage_service.read_document_image_bytes(str(tmp_path))
        native_text = storage_service.extract_document_text(str(tmp_path))
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    # Nativen Textlayer versuchen (schneller + günstiger) — Vision nur als Fallback
    if native_text:
        log.info("Rechnungsanalyse via Textlayer (%d Zeichen)", len(native_text))
        result = await analyze_invoice_from_text(native_text)
    else:
        log.info("Kein Textlayer — Rechnungsanalyse via Vision")
        result = await analyze_invoice(images)
    return InvoiceAnalysisPreview(
        purchase_date=result.purchase_date,
        amount_eur=result.amount_eur,
        produkt_name=result.produkt_name,
        notes=result.notes,
    )


@router.post("", response_model=InvoiceRead, status_code=status.HTTP_201_CREATED)
async def upload_invoice(
    product_id: int = Form(...),
    file: UploadFile = File(...),
    purchase_date: str | None = Form(None),
    amount_eur: float | None = Form(None),
    notes: str | None = Form(None),
    db: Session = Depends(get_db),
) -> Invoice:
    """Lädt eine Rechnung für ein Produkt hoch."""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Produkt nicht gefunden")

    # Begrenzt einlesen, damit übergroße Uploads nicht komplett im RAM landen;
    # validate_upload lehnt alles über dem Rechnungs-Limit ab.
    content = await file.read(settings.max_invoice_upload_bytes + 1)
    try:
        storage_service.validate_upload(
            file.filename or "rechnung", content, max_bytes=settings.max_invoice_upload_bytes
        )
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    pd: date | None = None
    if purchase_date:
        try:
            pd = date.fromisoformat(purchase_date)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Ungültiges Kaufdatum (YYYY-MM-DD erwartet)") from e

    if amount_eur is not None and (amount_eur < 0 or amount_eur > 1_000_000):
        raise HTTPException(status_code=400, detail="Betrag außerhalb des erlaubten Bereichs (0–1.000.000)")
    if notes is not None and len(notes) > 2000:
        raise HTTPException(status_code=400, detail="Notizen zu lang (max. 2000 Zeichen)")

    retain = _compute_retain_until(pd, product)

    stored_path, mime = storage_service.store_invoice(
        content=content,
        original_filename=file.filename or "rechnung",
        product_name=product.name,
        ref_date=pd or product.purchase_date,
    )

    invoice = Invoice(
        product_id=product_id,
        original_filename=file.filename or "rechnung",
        stored_path=str(stored_path),
        mime_type=mime,
        purchase_date=pd,
        amount_eur=amount_eur,
        retain_until=retain,
        notes=notes,
    )
    db.add(invoice)
    db.commit()
    db.refresh(invoice)
    return invoice


@router.get("", response_model=list[InvoiceRead])
def list_all_invoices(
    product_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Invoice]:
    """Alle Rechnungen, optional gefiltert nach Produkt.

    Sortierung: kürzeste Aufbewahrungsfrist zuerst (retain_until ASC),
    bei gleicher Frist neueste Rechnungen oben (purchase_date DESC).
    """
    q = db.query(Invoice)
    if product_id is not None:
        q = q.filter(Invoice.product_id == product_id)
    return q.order_by(Invoice.retain_until, Invoice.purchase_date.desc().nullslast()).all()


@router.get("/{invoice_id}", response_model=InvoiceRead)
def get_invoice(invoice_id: int, db: Session = Depends(get_db)) -> Invoice:
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    return inv


@router.get("/{invoice_id}/download")
def download_invoice(invoice_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Liefert die gespeicherte Rechnungsdatei als Download (Originaldateiname)."""
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    base = settings.invoices_dir.resolve()
    path = Path(inv.stored_path).resolve()
    if not path.is_relative_to(base) or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Rechnungsdatei nicht mehr vorhanden"
        )
    # filename setzt Content-Disposition: attachment — Datei wird heruntergeladen,
    # nicht im Browser gerendert
    return FileResponse(path, media_type=inv.mime_type, filename=inv.original_filename)


@router.delete("/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_invoice(invoice_id: int, force: bool = False, db: Session = Depends(get_db)) -> None:
    """Löscht eine Rechnung.

    Während der Aufbewahrungsfrist nur mit ?force=true (explizite Bestätigung
    im Frontend) — z. B. für versehentlich hochgeladene Dateien.
    """
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")

    if inv.retain_until > date.today() and not force:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Aufbewahrungsfrist läuft noch bis {inv.retain_until.isoformat()}. "
                "Zum Löschen trotz Frist die Bestätigung im Lösch-Dialog verwenden."
            ),
        )
    if force and inv.retain_until > date.today():
        log.info("Rechnung %d trotz laufender Frist (bis %s) gelöscht", inv.id, inv.retain_until)

    base = settings.invoices_dir.resolve()
    try:
        path = Path(inv.stored_path).resolve()
        if path.is_relative_to(base):
            path.unlink(missing_ok=True)
    except OSError as e:
        log.warning("Rechnungsdatei konnte nicht gelöscht werden (invoice=%d): %s", inv.id, e)
    db.delete(inv)
    db.commit()
