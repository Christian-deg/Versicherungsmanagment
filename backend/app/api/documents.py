"""Document Upload + Analyse + Bestätigung."""
from __future__ import annotations

import logging
import uuid
from pathlib import Path

from agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.agents.classifier_agent import classify_document
from app.agents.document_agent import analyze_document
from app.config import settings
from app.models.database import get_db
from app.models.models import Document, Insurance, Recommendation
from app.schemas.schemas import (
    DocumentClassification,
    DocumentRead,
    ExtractionPreview,
    InsuranceConfirmPayload,
    InsuranceRead,
    RecommendationRead,
)
from app.services import embedding_service, recommendation_service, storage_service

log = logging.getLogger(__name__)
router = APIRouter()


def _rag_metadata(ins: Insurance, ai_summary: str | None = None) -> str:
    """Erzeugt den Metadaten-Block für RAG (gemeinsam für primäres und Extra-Dokument)."""
    if ins.kuendigung_bis_tag and ins.kuendigung_bis_monat:
        kuendigung = f"jährlich kündbar bis {ins.kuendigung_bis_tag:02d}.{ins.kuendigung_bis_monat:02d}."
        if ins.kuendigung_zum_tag and ins.kuendigung_zum_monat:
            zum = f"{ins.kuendigung_zum_tag:02d}.{ins.kuendigung_zum_monat:02d}."
            kuendigung += f", Vertrag endet dann zum {zum}"
    else:
        kuendigung = "nicht angegeben"
    text = (
        f"Versicherung: {ins.name}\nKategorie: {ins.kategorie.value}\n"
        f"Versicherer: {ins.versicherer}\nVertragsnummer: {ins.vertragsnummer}\n"
        f"Laufzeit: {ins.start_date} bis {ins.end_date}\n"
        f"Prämie: {ins.praemie_eur} EUR ({ins.zahlungsintervall.value})\n"
        f"Kündigung: {kuendigung}\n"
        f"Notizen: {ins.notes or ''}"
    )
    if ai_summary:
        text += f"\nKI-Hinweise: {ai_summary}"
    return text


async def _embed_document_task(
    insurance_id: int, document_id: int, base_text: str, stored_path: str
) -> None:
    """Hintergrund-Task: Volltext extrahieren (ggf. Vision-OCR) und in den Vektorindex embedden.

    Läuft nach der Response, damit mehrseitige Scans (Vision-OCR pro Seite) den
    Request nicht in ein Timeout treiben. Vollständig fail-safe — Fehler landen
    nur im Log, nie beim Client. Nimmt bewusst nur Skalare entgegen (keine
    ORM-Objekte), da die DB-Session nach der Response geschlossen ist.
    """
    rag_text = base_text
    try:
        fulltext = storage_service.extract_document_text(stored_path)
        if not fulltext:
            log.info("Kein Textlayer — starte Vision-OCR für Dokument %d", document_id)
            fulltext = await embedding_service.ocr_document_text(stored_path)
        if fulltext:
            rag_text = rag_text + "\n\n--- Dokumentvolltext ---\n\n" + fulltext
            log.info("Volltext eingebettet (%d Zeichen) für Dokument %d", len(fulltext), document_id)
        else:
            log.info("Kein Volltext extrahierbar für Dokument %d", document_id)
    except Exception:  # noqa: BLE001
        log.warning("Volltext-Extraktion fehlgeschlagen (doc=%d) — nur Metadaten eingebettet", document_id)
    try:
        await embedding_service.embed_and_store(insurance_id, document_id, rag_text)
    except Exception:  # noqa: BLE001
        log.exception("Embedding fehlgeschlagen für Dokument %d", document_id)


@router.post("/classify", response_model=DocumentClassification)
async def classify_uploaded_document(
    file: UploadFile = File(...),
) -> DocumentClassification:
    """Erkennt automatisch, ob ein Upload eine Versicherung oder eine Rechnung ist.

    Günstiger Vorab-Check (Mini-Modell, Textlayer bevorzugt, Vision nur mit der
    ersten Seite). Die Datei wird dabei nicht gespeichert — das Frontend leitet
    anhand des Ergebnisses in den passenden Ablauf weiter.
    """
    # Großzügigstes Limit, da der Typ noch unbekannt ist
    classify_limit = max(settings.max_upload_bytes, settings.max_invoice_upload_bytes)
    content = await file.read(classify_limit + 1)
    try:
        suffix, _ = storage_service.validate_upload(
            file.filename or "upload", content, max_bytes=classify_limit
        )
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    incoming = settings.documents_dir.resolve() / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    tmp_path = incoming / f"_classify_{uuid.uuid4().hex}{suffix}"
    tmp_path.write_bytes(content)

    try:
        try:
            text = storage_service.extract_document_text(str(tmp_path))
        except storage_service.StorageError as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
        first_page: bytes | None = None
        if not text:
            try:
                images = storage_service.read_document_image_bytes(str(tmp_path))
                first_page = images[0] if images else None
            except storage_service.StorageError as e:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    finally:
        tmp_path.unlink(missing_ok=True)

    result = await classify_document(text, first_page)
    return DocumentClassification(typ=result.typ.value, begruendung=result.begruendung)


@router.post("/upload", response_model=ExtractionPreview)
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> ExtractionPreview:
    """Lädt PDF/JPEG/PNG hoch, analysiert via DocumentAnalysisAgent, gibt Vorschau zurück.

    Datei wird zunächst unter 'incoming' abgelegt; Versicherungs-Eintrag wird erst
    bei der Bestätigung (POST /confirm) erstellt.
    """
    # Begrenzt einlesen, damit übergroße Uploads nicht komplett im RAM landen;
    # validate_upload lehnt alles über max_upload_bytes ab.
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        suffix, mime = storage_service.validate_upload(file.filename or "upload", content)
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    # Vorab-Speicherung in 'incoming' (UUID-Name) für die Analyse
    incoming = settings.documents_dir.resolve() / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    tmp_path = incoming / f"{uuid.uuid4().hex}{suffix}"
    tmp_path.write_bytes(content)

    # Bilder extrahieren (PDF → PNG-Seiten oder direktes Bild)
    try:
        images = storage_service.read_document_image_bytes(str(tmp_path))
    except storage_service.StorageError as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
    if not images:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dokument enthält keine lesbaren Seiten.",
        )

    try:
        result = await analyze_document(images, file.filename or "upload")
    except OutputGuardrailTripwireTriggered as e:
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Dokument wurde vom Sicherheitsfilter abgelehnt.",
        ) from e
    except Exception as e:
        # Interne Fehlerdetails nur ins Log — nicht an den Client leaken
        log.exception("Dokumentenanalyse fehlgeschlagen")
        tmp_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="KI-Analyse fehlgeschlagen. Details siehe Server-Log.",
        ) from e

    # Document-Eintrag (noch ohne insurance_id) anlegen
    doc = Document(
        insurance_id=None,
        original_filename=file.filename or "upload",
        stored_path=str(tmp_path),
        mime_type=mime,
        ai_summary=result.hinweise,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return ExtractionPreview(
        versicherer=result.versicherer,
        kategorie=result.kategorie,
        vertragsnummer=result.vertragsnummer,
        start_date=result.start_date,
        end_date=result.end_date,
        praemie_eur=result.praemie_eur,
        zahlungsintervall=result.zahlungsintervall,
        kuendigung_bis_tag=result.kuendigung_bis_tag,
        kuendigung_bis_monat=result.kuendigung_bis_monat,
        kuendigung_zum_tag=result.kuendigung_zum_tag,
        kuendigung_zum_monat=result.kuendigung_zum_monat,
        konfidenz=result.konfidenz,
        hinweise=result.hinweise,
        document_id=doc.id,
    )


@router.post("/upload-extra", response_model=DocumentRead)
async def upload_document_extra(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Document:
    """Speichert ein weiteres Dokument ohne KI-Analyse für die spätere Zuordnung.

    Wird verwendet um beim Anlegen einer Versicherung mehrere Dokumente hochzuladen.
    Das Dokument landet zunächst unter '_incoming' und wird beim Confirm verschoben.
    """
    content = await file.read(settings.max_upload_bytes + 1)
    try:
        suffix, mime = storage_service.validate_upload(file.filename or "upload", content)
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    incoming = settings.documents_dir.resolve() / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    tmp_path = incoming / f"{uuid.uuid4().hex}{suffix}"
    tmp_path.write_bytes(content)

    doc = Document(
        insurance_id=None,
        original_filename=file.filename or "upload",
        stored_path=str(tmp_path),
        mime_type=mime,
        ai_summary=None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.post("/confirm/{document_id}", response_model=InsuranceRead)
async def confirm_extraction(
    document_id: int,
    payload: InsuranceConfirmPayload,
    background: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Insurance:
    """Bestätigt das (ggf. korrigierte) Extraktionsergebnis und legt die Versicherung an.

    - Erstellt Insurance-Eintrag
    - Verschiebt das Dokument in den finalen Ordner (kategorie/versicherer/jahr)
    - Embedded den OCR-Text (hinweise + Felder) in den Vektorindex
    - Verknüpft und embedded optionale Extra-Dokumente (multi-upload)
    """
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")
    if doc.insurance_id is not None:
        raise HTTPException(status_code=400, detail="Dokument ist bereits zugeordnet")

    # Insurance anlegen (extra_document_ids gehört nicht zum ORM-Modell)
    ins_data = payload.model_dump(exclude={"extra_document_ids"})
    ins = Insurance(**ins_data)
    db.add(ins)
    db.flush()  # ID erhalten

    # Datei in finalen Ordner verschieben
    src = Path(doc.stored_path)
    if not src.exists():
        raise HTTPException(status_code=410, detail="Quelldatei nicht mehr vorhanden")
    content = src.read_bytes()
    final_path, _ = storage_service.store_document(
        content=content,
        original_filename=doc.original_filename,
        kategorie=ins.kategorie,
        versicherer=ins.versicherer,
        ref_date=ins.start_date,
    )
    src.unlink(missing_ok=True)
    doc.stored_path = str(final_path)
    doc.insurance_id = ins.id
    db.commit()
    db.refresh(ins)

    # Embedding (inkl. evtl. Vision-OCR) nach der Response — verhindert Timeouts
    background.add_task(
        _embed_document_task, ins.id, doc.id, _rag_metadata(ins, doc.ai_summary), doc.stored_path
    )

    # Weitere Dokumente zuordnen (multi-upload beim Anlegen)
    for extra_id in payload.extra_document_ids:
        extra_doc = db.get(Document, extra_id)
        if not extra_doc:
            log.warning("Extra-Dokument %d übersprungen: nicht gefunden", extra_id)
            continue
        if extra_doc.insurance_id is not None:
            log.warning("Extra-Dokument %d übersprungen: bereits einer Versicherung zugeordnet", extra_id)
            continue
        extra_src = Path(extra_doc.stored_path)
        if not extra_src.exists():
            log.warning("Extra-Dokument %d: Quelldatei nicht mehr vorhanden", extra_id)
            continue
        extra_content = extra_src.read_bytes()
        try:
            extra_final_path, _ = storage_service.store_document(
                content=extra_content,
                original_filename=extra_doc.original_filename,
                kategorie=ins.kategorie,
                versicherer=ins.versicherer,
                ref_date=ins.start_date,
            )
        except storage_service.StorageError as e:
            log.warning("Extra-Dokument %d konnte nicht verschoben werden: %s", extra_id, e)
            continue
        extra_src.unlink(missing_ok=True)
        extra_doc.stored_path = str(extra_final_path)
        extra_doc.insurance_id = ins.id
        db.commit()

        background.add_task(
            _embed_document_task, ins.id, extra_doc.id, _rag_metadata(ins), extra_doc.stored_path
        )

    return ins


@router.get("", response_model=list[DocumentRead])
def list_documents(
    insurance_id: int | None = None,
    db: Session = Depends(get_db),
) -> list[Document]:
    """Listet Dokumente, optional gefiltert nach Versicherung (neueste zuerst)."""
    q = db.query(Document)
    if insurance_id is not None:
        q = q.filter(Document.insurance_id == insurance_id)
    return q.order_by(Document.uploaded_at.desc()).all()


@router.post("/attach/{insurance_id}", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def attach_document(
    insurance_id: int,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> Document:
    """Hängt ein weiteres Dokument an eine bestehende Versicherung an.

    Für jährlich neu eintreffende Unterlagen (Beitragsrechnung, neue Police etc.).
    Keine KI-Feldextraktion — das Dokument wird gespeichert, volltextindiziert
    (inkl. Vision-OCR-Fallback im Hintergrund) und ist damit im Chat auffindbar.
    """
    ins = db.get(Insurance, insurance_id)
    if not ins:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")

    content = await file.read(settings.max_upload_bytes + 1)
    try:
        final_path, mime = storage_service.store_document(
            content=content,
            original_filename=file.filename or "dokument",
            kategorie=ins.kategorie,
            versicherer=ins.versicherer,
            ref_date=None,  # Ablage im Jahresordner des Uploads
        )
    except storage_service.StorageError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e

    doc = Document(
        insurance_id=ins.id,
        original_filename=file.filename or "dokument",
        stored_path=str(final_path),
        mime_type=mime,
        ai_summary=None,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background.add_task(_embed_document_task, ins.id, doc.id, _rag_metadata(ins), doc.stored_path)
    return doc


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, db: Session = Depends(get_db)) -> None:
    """Löscht ein einzelnes Dokument samt Datei und RAG-Embeddings."""
    doc = db.get(Document, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Dokument nicht gefunden")

    base = settings.documents_dir.resolve()
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
    db.delete(doc)
    db.commit()


@router.get("/{insurance_id}/recommendation", response_model=RecommendationRead)
def get_recommendation(insurance_id: int, db: Session = Depends(get_db)) -> Recommendation:
    """Gibt die gespeicherte Empfehlung zurück (404, wenn noch keine erzeugt wurde)."""
    ins = db.get(Insurance, insurance_id)
    if not ins:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")
    if ins.recommendation is None:
        raise HTTPException(status_code=404, detail="Noch keine Empfehlung vorhanden")
    return ins.recommendation


@router.post("/{insurance_id}/recommendation", response_model=RecommendationRead)
async def create_recommendation(insurance_id: int, db: Session = Depends(get_db)) -> Recommendation:
    """Erzeugt (oder erneuert) die Empfehlung für eine Versicherung und speichert sie."""
    ins = db.get(Insurance, insurance_id)
    if not ins:
        raise HTTPException(status_code=404, detail="Versicherung nicht gefunden")
    try:
        return await recommendation_service.generate_for_insurance(db, ins)
    except (InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered) as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Empfehlung wurde vom Sicherheitsfilter blockiert.",
        ) from e
    except Exception as e:
        log.exception("Empfehlung fehlgeschlagen")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Empfehlung fehlgeschlagen. Details siehe Server-Log.",
        ) from e

