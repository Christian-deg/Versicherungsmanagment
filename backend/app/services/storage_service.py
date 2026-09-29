"""Sichere Dokumenten-Ablage mit UUID-Dateinamen + Pfad-Traversal-Schutz."""
from __future__ import annotations

import base64
import io
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


# Obergrenze der gerenderten Pixel je PDF-Seite (A4 bei 150 dpi ≈ 2,2 MP;
# 20 MP ≈ 60 MB unkomprimiert) — Schutz vor Dekompressions-Bomben
_MAX_PAGE_PIXELS = 20_000_000

# Längste Bildkante für KI-Analysen: OpenAI skaliert größere Bilder ohnehin
# herunter — kleinere Payloads sparen Upload-Zeit und Tokens
_MAX_IMAGE_EDGE = 2048


def image_data_url(img: bytes) -> str:
    """Base64-Data-URL mit dem tatsächlichen Bildformat (JPEG oder PNG).

    Handyfotos sind JPEG — sie als image/png zu deklarieren ist falsch und
    hängt davon ab, dass die API das Format selbst erkennt.
    """
    mime = "image/jpeg" if img.startswith(MAGIC_BYTES[".jpg"]) else "image/png"
    return f"data:{mime};base64,{base64.b64encode(img).decode('ascii')}"


def _normalize_image(data: bytes) -> bytes:
    """Dreht Fotos gemäß EXIF-Ausrichtung und verkleinert große Bilder für die KI.

    Unverändert zurück, wenn nichts zu tun ist oder das Bild nicht lesbar ist
    (die KI-Analyse bekommt dann das Original — wie bisher).
    """
    from PIL import Image, ImageOps

    try:
        with Image.open(io.BytesIO(data)) as img:
            fmt = img.format
            orientation = img.getexif().get(0x0112, 1)  # EXIF-Tag "Orientation"
            if orientation == 1 and max(img.size) <= _MAX_IMAGE_EDGE:
                return data
            if fmt == "JPEG":
                # Dekodiert direkt verkleinert (DCT-Skalierung) — spart RAM bei 50-MP-Fotos
                img.draft("RGB", (_MAX_IMAGE_EDGE, _MAX_IMAGE_EDGE))
            out = ImageOps.exif_transpose(img)
            out.thumbnail((_MAX_IMAGE_EDGE, _MAX_IMAGE_EDGE))
            buf = io.BytesIO()
            if fmt == "JPEG":
                out.convert("RGB").save(buf, format="JPEG", quality=90)
            else:
                out.save(buf, format="PNG")
            return buf.getvalue()
    except Exception as e:  # noqa: BLE001
        log.warning("Bild konnte nicht normalisiert werden — verwende Original: %s", e)
        return data


def validate_upload(filename: str, content: bytes, max_bytes: int | None = None) -> tuple[str, str]:
    """Prüft Dateiname, Suffix, Größe und Magic-Bytes. Gibt (suffix, mime) zurück.

    max_bytes: Größenlimit; Standard ist settings.max_upload_bytes (Dokumente).
    Rechnungen verwenden das größere settings.max_invoice_upload_bytes.
    """
    limit = max_bytes if max_bytes is not None else settings.max_upload_bytes
    if len(content) > limit:
        mb = limit / (1024 * 1024)
        raise StorageError(f"Datei zu groß: {len(content)} Bytes (max {mb:.0f} MB)")
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
    suffix, mime = validate_upload(original_filename, content, max_bytes=settings.max_invoice_upload_bytes)

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


def resolve_stored_path(stored_path: str, base: Path) -> Path | None:
    """Löst einen in der DB gespeicherten Pfad sicher gegen das aktuelle Datenverzeichnis auf.

    stored_path kann aus einer anderen Umgebung stammen (Docker: /app/data/…,
    lokal: .\\data\\…) — die Dateien sind per Volume dieselben. Liegt der Pfad
    nicht direkt unterhalb von base, wird der Teil hinter dem base-Ordnernamen
    (z.B. 'documents') gegen base neu verankert. Gibt None zurück, wenn der
    Pfad nicht sicher innerhalb von base auflösbar ist (Traversal-Schutz).
    """
    base = base.resolve()
    p = Path(stored_path)
    try:
        rp = p.resolve()
        if rp.is_relative_to(base):
            return rp
    except OSError:
        pass
    parts = p.as_posix().split("/")
    if base.name in parts:
        tail = parts[parts.index(base.name) + 1 :]
        if tail:
            candidate = base.joinpath(*tail).resolve()
            if candidate.is_relative_to(base):
                return candidate
    return None


def delete_stored_file(stored_path: str, base: Path) -> bool:
    """Löscht eine gespeicherte Datei sicher (Pfad wird via resolve_stored_path gegen base verankert).

    Dieselbe Umgebungs-Umverankerung (Docker ↔ lokal) wie beim Lesen — sonst
    bleiben nach einem Umgebungswechsel beim Löschen still Datei-Leichen liegen.
    Gibt False zurück, wenn der Pfad nicht auflösbar ist oder das Löschen fehlschlägt.
    """
    path = resolve_stored_path(stored_path, base)
    if path is None:
        log.warning("Pfad nicht sicher auflösbar — Datei nicht gelöscht: %s", stored_path)
        return False
    try:
        path.unlink(missing_ok=True)
    except OSError as e:
        log.warning("Datei konnte nicht gelöscht werden (%s): %s", path.name, e)
        return False
    return True


def read_document_image_bytes(stored_path: str) -> list[bytes]:
    """Liest ein gespeichertes Dokument und gibt eine Liste von Bildern (PNG/JPEG) zurück.

    PDFs werden via PyMuPDF in PNG-Bilder gerendert. Fotos werden gemäß EXIF
    gedreht und auf max. _MAX_IMAGE_EDGE verkleinert (Format bleibt erhalten).
    Für die KI-Übergabe image_data_url() verwenden (setzt den passenden MIME-Typ).
    """
    base = settings.documents_dir.resolve()
    path = resolve_stored_path(stored_path, base)
    if path is None:
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
                    # Pixel-Deckel gegen PDF-Bomben: eine präparierte Seite mit
                    # riesigen Abmessungen würde bei fixen 150 dpi unkomprimiert
                    # hunderte MB allokieren (OOM). Zoom ggf. herunterskalieren.
                    zoom = 150 / 72
                    pixels = (page.rect.width * zoom) * (page.rect.height * zoom)
                    if pixels > _MAX_PAGE_PIXELS:
                        zoom *= (_MAX_PAGE_PIXELS / pixels) ** 0.5
                    pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom))
                    images.append(pix.tobytes("png"))
                    del pix  # unkomprimierte Pixeldaten sofort freigeben
        except Exception as e:
            # Korrupte/nicht parsbare PDFs sollen einen definierten Fehler liefern (kein 500)
            raise StorageError(f"PDF konnte nicht gelesen werden: {path.name}") from e
        return images

    return [_normalize_image(path.read_bytes())]


def extract_document_text(stored_path: str) -> str:
    """Extrahiert den Volltext aus einem gespeicherten Dokument für RAG.

    PDFs: PyMuPDF-Textextraktion (max. 10 Seiten, nur wenn Textlayer vorhanden).
    Bilder (JPEG/PNG): leerer String — kein OCR ohne externe Bibliothek.

    Gibt den zusammengeführten Text aller Seiten zurück, oder '' wenn kein Text
    extrahierbar ist (gescannte PDFs ohne Textlayer, Bilder).
    """
    base = settings.documents_dir.resolve()
    path = resolve_stored_path(stored_path, base)
    if path is None:
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
