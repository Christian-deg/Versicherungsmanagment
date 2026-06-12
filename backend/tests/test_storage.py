"""Tests für Storage-Service: Magic-Bytes, Pfad-Traversal, Größe."""
from __future__ import annotations

import pytest

from app.models.enums import Kategorie
from app.services import storage_service


def test_validate_upload_pdf_ok() -> None:
    content = b"%PDF-1.4\n" + b"x" * 100
    suffix, mime = storage_service.validate_upload("test.pdf", content)
    assert suffix == ".pdf"
    assert mime == "application/pdf"


def test_validate_upload_png_ok() -> None:
    content = b"\x89PNG\r\n\x1a\n" + b"x" * 100
    suffix, mime = storage_service.validate_upload("scan.png", content)
    assert suffix == ".png"
    assert mime == "image/png"


def test_validate_upload_wrong_magic() -> None:
    content = b"NOTAPDF" + b"x" * 100
    with pytest.raises(storage_service.StorageError, match="Magic-Bytes"):
        storage_service.validate_upload("fake.pdf", content)


def test_validate_upload_disallowed_suffix() -> None:
    with pytest.raises(storage_service.StorageError, match="nicht erlaubt"):
        storage_service.validate_upload("evil.exe", b"MZ" + b"x" * 100)


def test_validate_upload_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "max_upload_bytes", 100)
    with pytest.raises(storage_service.StorageError, match="zu groß"):
        storage_service.validate_upload("big.pdf", b"%PDF-" + b"x" * 200)


def test_extract_document_text_pdf(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """extract_document_text gibt Seitentext aus einem echten PDF zurück."""
    import pymupdf

    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir(parents=True)

    # Minimales PDF mit Text via PyMuPDF erzeugen
    pdf_path = docs_dir / "test.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "Selbstbehalt: 500 EUR")
        doc.save(str(pdf_path))

    result = storage_service.extract_document_text(str(pdf_path))
    assert "Selbstbehalt" in result
    assert "[Seite 1]" in result


def test_extract_document_text_image_returns_empty(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """extract_document_text gibt '' für Bilder zurück (kein OCR)."""
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    docs_dir = tmp_path / "documents"
    docs_dir.mkdir(parents=True)

    png_path = docs_dir / "scan.png"
    png_path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    result = storage_service.extract_document_text(str(png_path))
    assert result == ""


def test_extract_document_text_traversal_blocked(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    """extract_document_text blockiert Pfad-Traversal."""
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "documents").mkdir(parents=True)

    with pytest.raises(storage_service.StorageError, match="außerhalb"):
        storage_service.extract_document_text("/etc/passwd")


def test_store_document_traversal_safe(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "max_upload_bytes", 10 * 1024 * 1024)
    (tmp_path / "documents").mkdir(parents=True, exist_ok=True)

    content = b"%PDF-1.4\n" + b"x" * 100
    # Versicherer mit Path-Traversal-Versuch
    path, mime = storage_service.store_document(
        content=content,
        original_filename="police.pdf",
        kategorie=Kategorie.KFZ,
        versicherer="../../etc/passwd",
    )
    assert mime == "application/pdf"
    # Pfad muss innerhalb von documents_dir liegen
    assert str(path).startswith(str(settings.documents_dir.resolve()))
    assert ".." not in str(path)
