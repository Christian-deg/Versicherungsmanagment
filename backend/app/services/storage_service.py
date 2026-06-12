"""Sichere Dokumenten-Ablage mit UUID-Dateinamen + Pfad-Traversal-Schutz."""
from __future__ import annotations

import logging
import uuid
from datetime import date
from pathlib import Path

from app.config import settings
from app.models.enums import Kategorie

log = logging.getLogger(__name__)

# Magic-Bytes-Validierung (LLM04)
MAGIC_BYTES: dict[str, bytes] = {
    ".pdf": b"%PDF-",
    ".png": b"\x89PNG\r\n\x1a\n",
    ".jpg": b"\xff\xd8\xff",
    ".jpeg": b"\xff\xd8\xff",
}
ALLOWED_MIME = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}


class StorageError(ValueError):
    pass


def validate_upload(filename: str, content: bytes) -> tuple[str, str]:
    """Prüft Dateiname, Suffix, Größe und Magic-Bytes. Gibt (suffix, mime) zurück."""
    if len(content) > settings.max_upload_bytes:
        raise StorageError(f"Datei zu groß: {len(content)} Bytes (max {settings.max_upload_bytes})")
    if len(content) < 16:
        raise StorageError("Datei zu klein / leer")

    suffix = Path(filename).suffix.lower()
    if suffix not in MAGIC_BYTES:
        raise StorageError(f"Dateityp '{suffix}' nicht erlaubt. Erlaubt: {list(MAGIC_BYTES)}")

    expected = MAGIC_BYTES[suffix]
    if not content.startswith(expected):
        raise StorageError(f"Falsche Magic-Bytes für Typ '{suffix}'")
    return suffix, ALLOWED_MIME[suffix]


def store_document(
    content: bytes,
    original_filename: str,
    kategorie: Kategorie,
    versicherer: str,
    ref_date: date | None = None,
) -> tuple[Path, str]:
    """Speichert das Dokument unter `data/documents/{kat}/{vers}/{jahr}/<uuid>.<ext>`.

    Gibt (resolved_path, mime_type) zurück.
    Pfad-Traversal-Schutz: alle Teile werden via Slug bereinigt und Path.resolve()
    muss innerhalb des documents_dir liegen.
    """
    suffix, mime = validate_upload(original_filename, content)

    year = (ref_date or date.today()).year
    base = settings.documents_dir.resolve()

    # Slug-basiert: nur erlaubte Zeichen, keine Pfadtrenner
    safe_versicherer = _slug(versicherer) or "unbekannt"
    safe_kategorie = kategorie.value  # Enum-Wert ist bekannt/sicher

    target_dir = (base / safe_kategorie / safe_versicherer / str(year)).resolve()
    if not target_dir.is_relative_to(base):
        raise StorageError("Pfad-Traversal erkannt")
    target_dir.mkdir(parents=True, exist_ok=True)

    new_name = f"{uuid.uuid4().hex}{suffix}"
    target_path = (target_dir / new_name).resolve()
    if not target_path.is_relative_to(base):
        raise StorageError("Pfad-Traversal erkannt")

    target_path.write_bytes(content)
    log.info("Dokument gespeichert: %s (%d Bytes)", target_path.relative_to(base), len(content))
    return target_path, mime


def store_invoice(
    content: bytes,
    original_filename: str,
    product_name: str,
    ref_date: date | None = None,
) -> tuple[Path, str]:
    """Speichert eine Rechnung unter `data/invoices/{produktname}/{jahr}/<uuid>.<ext>`.

    Gibt (resolved_path, mime_type) zurück.
    """
    suffix, mime = validate_upload(original_filename, content)

    year = (ref_date or date.today()).year
    base = settings.invoices_dir.resolve()

    safe_product = _slug(product_name) or "unbekannt"
    target_dir = (base / safe_product / str(year)).resolve()
    if not target_dir.is_relative_to(base):
        raise StorageError("Pfad-Traversal erkannt")
    target_dir.mkdir(parents=True, exist_ok=True)

    new_name = f"{uuid.uuid4().hex}{suffix}"
    target_path = (target_dir / new_name).resolve()
    if not target_path.is_relative_to(base):
        raise StorageError("Pfad-Traversal erkannt")

    target_path.write_bytes(content)
    log.info("Rechnung gespeichert: %s (%d Bytes)", target_path.relative_to(base), len(content))
    return target_path, mime


def _slug(text: str) -> str:
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
    return "".join(c if c in allowed else "_" for c in text.strip())[:50]


def read_document_image_bytes(stored_path: str) -> list[bytes]:
    """Liest ein gespeichertes Dokument und gibt eine Liste von PNG-Bildern zurück.

    PDFs werden via PyMuPDF in PNG-Bilder gerendert.
    Bilder werden direkt zurückgegeben.
    """
    base = settings.documents_dir.resolve()
    path = Path(stored_path).resolve()
    if not path.is_relative_to(base):
        raise StorageError("Pfad außerhalb des Dokumentenverzeichnisses")
    if not path.exists():
        raise StorageError(f"Datei nicht gefunden: {path.name}")

    if path.suffix.lower() == ".pdf":
        import pymupdf  # PyMuPDF

        images: list[bytes] = []
        try:
            with pymupdf.open(path) as doc:
                # Maximal 10 Seiten analysieren (LLM10)
                for page in doc.pages(stop=10):
                    pix = page.get_pixmap(dpi=150)
                    images.append(pix.tobytes("png"))
                    del pix  # unkomprimierte Pixeldaten sofort freigeben
        except Exception as e:
            # Korrupte/nicht parsbare PDFs sollen einen definierten Fehler liefern (kein 500)
            raise StorageError(f"PDF konnte nicht gelesen werden: {path.name}") from e
        return images

    return [path.read_bytes()]


def extract_document_text(stored_path: str) -> str:
    """Extrahiert den Volltext aus einem gespeicherten Dokument für RAG.

    PDFs: PyMuPDF-Textextraktion (max. 10 Seiten, nur wenn Textlayer vorhanden).
    Bilder (JPEG/PNG): leerer String — kein OCR ohne externe Bibliothek.

    Gibt den zusammengeführten Text aller Seiten zurück, oder '' wenn kein Text
    extrahierbar ist (gescannte PDFs ohne Textlayer, Bilder).
    """
    base = settings.documents_dir.resolve()
    path = Path(stored_path).resolve()
    if not path.is_relative_to(base):
        raise StorageError("Pfad außerhalb des Dokumentenverzeichnisses")
    if not path.exists():
        raise StorageError(f"Datei nicht gefunden: {path.name}")

    if path.suffix.lower() != ".pdf":
        return ""  # Bilder: kein Volltext ohne OCR

    import pymupdf  # PyMuPDF

    pages: list[str] = []
    try:
        with pymupdf.open(path) as doc:
            for i, page in enumerate(doc.pages(stop=10)):
                text = page.get_text("text").strip()
                if text:
                    pages.append(f"[Seite {i + 1}]\n{text}")
    except Exception as e:
        raise StorageError(f"PDF konnte nicht gelesen werden: {path.name}") from e
    return "\n\n".join(pages)
