"""Rechnungs-Upload und -Verwaltung je Produkt."""
from __future__ import annotations

import logging
from datetime import date, timedelta
from pathlib import Path

import anyio.to_thread
from agents.exceptions import OutputGuardrailTripwireTriggered
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.agents.invoice_agent import InvoiceExtraction, analyze_invoice, analyze_invoice_from_text
from app.config import settings
from app.models.database import get_db
from app.models.models import Invoice, Product
from app.schemas.schemas import InvoiceAnalysisPreview, InvoiceRead, InvoiceUpdate
from app.services import ki_fehler, storage_service

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


async def _analyze_stored_invoice(tmp_path: Path) -> InvoiceExtraction:
    """Textlayer zuerst (schnell, günstig); Vision, wenn der Text keine Kerndaten liefert.

    Scanner-PDFs haben oft einen leeren oder unbrauchbaren Textlayer — dann
    muss das Bild ausgewertet werden. Wirft HTTPException bei Fehlschlag.
    """
    try:
        native_text = await anyio.to_thread.run_sync(storage_service.extract_document_text, str(tmp_path))
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    text_result: InvoiceExtraction | None = None
    if native_text.strip():
        log.info("Rechnungsanalyse via Textlayer (%d Zeichen)", len(native_text))
        try:
            text_result = await analyze_invoice_from_text(native_text)
        except Exception as e:  # noqa: BLE001
            if ki_fehler.ist_dauerhaft(e):
                # Guthaben leer / Key ungültig / Modell unbekannt: Vision scheitert genauso
                log.exception("Rechnungsanalyse via Textlayer fehlgeschlagen")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY, detail=await ki_fehler.melde_ki_fehler(e)
                ) from e
            log.warning("Rechnungsanalyse via Textlayer fehlgeschlagen — Vision-Fallback", exc_info=True)
        if text_result is not None and text_result.hat_kerndaten:
            return text_result
        if text_result is not None:
            log.info("Textlayer ohne Kaufdatum/Betrag — Vision-Fallback")
    else:
        log.info("Kein Textlayer — Rechnungsanalyse via Vision")

    try:
        images = await anyio.to_thread.run_sync(storage_service.read_document_image_bytes, str(tmp_path))
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    try:
        vision_result = await analyze_invoice(images)
    except OutputGuardrailTripwireTriggered as e:
        log.warning("Rechnungsanalyse (Vision) vom Sicherheitsfilter blockiert")
        if text_result is not None:
            return text_result
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Beleg wurde vom Sicherheitsfilter abgelehnt.",
        ) from e
    except Exception as e:  # noqa: BLE001
        log.exception("Rechnungsanalyse via Vision fehlgeschlagen")
        if text_result is not None:
            return text_result  # Teilergebnis aus dem Textlayer ist besser als nichts
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=await ki_fehler.melde_ki_fehler(e)
        ) from e
    return vision_result.ergaenzt_um(text_result)


@router.post("/analyze", response_model=InvoiceAnalysisPreview)
async def analyze_invoice_file(
    file: UploadFile = File(...),
) -> InvoiceAnalysisPreview:
    """Analysiert eine Rechnungsdatei per KI und gibt Kaufdatum, Betrag und Notiz zur
    Prüfung zurück. Der eigentliche Upload erfolgt erst nach Bestätigung.

    KI-Fehler liefern 502 mit verständlicher Meldung (z. B. "Guthaben aufgebraucht")
    statt einer leeren Extraktion.
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
    # Datei-I/O und PDF-Rendering blockieren — im Thread, damit der Event-Loop frei bleibt
    await anyio.to_thread.run_sync(tmp_path.write_bytes, content)
    try:
        result = await _analyze_stored_invoice(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)

    if not result.hat_kerndaten:
        log.info("Rechnungsanalyse ohne Kaufdatum und Betrag")
    return InvoiceAnalysisPreview(**result.model_dump())


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

    stored_path, mime = await anyio.to_thread.run_sync(
        storage_service.store_invoice,
        content,
        file.filename or "rechnung",
        product.name,
        pd or product.purchase_date,
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
    # Kaufdatum des Produkts aus der Rechnung übernehmen, falls noch nicht erfasst
    if pd and product.purchase_date is None:
        product.purchase_date = pd
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


@router.patch("/{invoice_id}", response_model=InvoiceRead)
def update_invoice(invoice_id: int, payload: InvoiceUpdate, db: Session = Depends(get_db)) -> Invoice:
    """Korrigiert Kaufdatum, Betrag oder Notiz einer Rechnung (z. B. vergessener Betrag).

    Nur mitgeschickte Felder ändern sich; ein explizites null leert das Feld.
    Bei geändertem Kaufdatum wird die Aufbewahrungsfrist neu berechnet und ein
    fehlendes Produkt-Kaufdatum ergänzt — wie beim Upload.
    """
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(inv, field, value)
    if "purchase_date" in changes:
        inv.retain_until = _compute_retain_until(inv.purchase_date, inv.product)
        if inv.purchase_date and inv.product.purchase_date is None:
            inv.product.purchase_date = inv.purchase_date
    db.commit()
    db.refresh(inv)
    return inv


def _resolve_invoice_file(db: Session, invoice_id: int) -> tuple[Invoice, Path]:
    """Lädt Rechnung + sicher aufgelösten Dateipfad (404/410 bei Problemen)."""
    inv = db.get(Invoice, invoice_id)
    if not inv:
        raise HTTPException(status_code=404, detail="Rechnung nicht gefunden")
    # resolve_stored_path verankert auch Pfade aus anderer Umgebung (Docker ↔ lokal)
    path = storage_service.resolve_stored_path(inv.stored_path, settings.invoices_dir)
    if path is None or not path.exists():
        raise HTTPException(
            status_code=status.HTTP_410_GONE, detail="Rechnungsdatei nicht mehr vorhanden"
        )
    return inv, path


@router.get("/{invoice_id}/download")
def download_invoice(invoice_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Liefert die gespeicherte Rechnungsdatei als Download (Originaldateiname)."""
    inv, path = _resolve_invoice_file(db, invoice_id)
    # filename setzt Content-Disposition: attachment — Datei wird heruntergeladen,
    # nicht im Browser gerendert
    return FileResponse(path, media_type=inv.mime_type, filename=inv.original_filename)


@router.get("/{invoice_id}/file")
def view_invoice_file(invoice_id: int, db: Session = Depends(get_db)) -> FileResponse:
    """Liefert die Rechnungsdatei zur Ansicht im Browser (inline) — wie bei Dokumenten."""
    inv, path = _resolve_invoice_file(db, invoice_id)
    return FileResponse(
        path,
        media_type=inv.mime_type,
        filename=inv.original_filename,
        content_disposition_type="inline",
    )


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

    stored_path = inv.stored_path
    db.delete(inv)
    db.commit()
    # Datei erst nach dem Commit löschen — scheitert der Commit (z. B. DB gesperrt),
    # bliebe sonst ein Rechnungs-Eintrag ohne Beleg-Datei zurück
    storage_service.delete_stored_file(stored_path, settings.invoices_dir)
