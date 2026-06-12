"""Tests für Vision-OCR in embedding_service."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pymupdf
import pytest


@pytest.fixture()
def pdf_with_text(tmp_path, monkeypatch):
    """Erzeugt ein echtes PDF mit Textlayer und patcht documents_dir."""
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    docs = tmp_path / "documents"
    docs.mkdir(parents=True)

    pdf_path = docs / "test.pdf"
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), "Selbstbehalt: 300 EUR. Deckungssumme: 50.000 EUR.")
        doc.save(str(pdf_path))
    return pdf_path


@pytest.fixture()
def scanned_pdf(tmp_path, monkeypatch):
    """Erzeugt ein PDF ohne Textlayer (nur Bild-Seite via PyMuPDF)."""
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    docs = tmp_path / "documents"
    docs.mkdir(parents=True)

    pdf_path = docs / "scan.pdf"
    with pymupdf.open() as doc:
        doc.new_page()  # leere Seite — kein Text
        doc.save(str(pdf_path))
    return pdf_path


async def test_ocr_always_calls_vision_for_pdf(pdf_with_text):
    """ocr_document_text verwendet immer Vision-API (egal ob Textlayer vorhanden).

    Die Entscheidung native vs. Vision liegt im Aufrufer (documents.py).
    """
    fake_message = SimpleNamespace(content="Deckungssumme: 100.000 EUR")
    fake_choice = SimpleNamespace(message=fake_message)
    fake_resp = SimpleNamespace(choices=[fake_choice])

    fake_completions = AsyncMock(return_value=fake_resp)
    fake_chat = MagicMock()
    fake_chat.completions.create = fake_completions
    fake_client = MagicMock()
    fake_client.chat = fake_chat

    from app.services import embedding_service

    with patch.object(embedding_service, "_client", return_value=fake_client):
        result = await embedding_service.ocr_document_text(str(pdf_with_text))

    assert fake_completions.called
    assert "Deckungssumme" in result


async def test_ocr_calls_vision_for_scanned_pdf(scanned_pdf):
    """Bei fehlendem Textlayer wird Vision-API aufgerufen."""
    fake_message = SimpleNamespace(content="Versicherungsbedingungen §1 Deckungsumfang")
    fake_choice = SimpleNamespace(message=fake_message)
    fake_resp = SimpleNamespace(choices=[fake_choice])

    fake_completions = AsyncMock(return_value=fake_resp)
    fake_chat = MagicMock()
    fake_chat.completions.create = fake_completions
    fake_client = MagicMock()
    fake_client.chat = fake_chat

    from app.services import embedding_service

    with patch.object(embedding_service, "_client", return_value=fake_client):
        result = await embedding_service.ocr_document_text(str(scanned_pdf))

    assert fake_completions.called
    assert "Versicherungsbedingungen" in result
    assert "[Seite 1]" in result


async def test_ocr_returns_empty_on_invalid_path(tmp_path, monkeypatch):
    """Ungültiger Pfad gibt leeren String zurück statt Exception."""
    from app.config import settings
    from app.services import embedding_service

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    (tmp_path / "documents").mkdir(parents=True)

    result = await embedding_service.ocr_document_text("/nonexistent/file.pdf")
    assert result == ""


async def test_ocr_handles_api_error_gracefully(scanned_pdf):
    """API-Fehler einzelner Seiten werden abgefangen — kein Absturz."""
    fake_completions = AsyncMock(side_effect=RuntimeError("OpenAI nicht erreichbar"))
    fake_chat = MagicMock()
    fake_chat.completions.create = fake_completions
    fake_client = MagicMock()
    fake_client.chat = fake_chat

    from app.services import embedding_service

    with patch.object(embedding_service, "_client", return_value=fake_client):
        result = await embedding_service.ocr_document_text(str(scanned_pdf))

    assert result == ""  # kein Crash, nur leerer Rückgabewert
