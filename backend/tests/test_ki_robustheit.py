"""Tests für die Robustheit der KI-Aufrufe.

Hintergrund: Ein aufgebrauchtes OpenAI-Guthaben ließ jede Rechnungsanalyse still
eine leere Extraktion liefern. Diese Tests sichern ab, dass KI-Fehler sichtbar
werden, der Vision-Fallback greift und Modell-Einstellungen zu gpt-5.x passen.
"""
from __future__ import annotations

import io
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import openai
import pymupdf
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _setup_db() -> None:
    from app.models.database import init_db

    init_db()


def _api_error(
    cls: type[openai.APIStatusError], status: int, code: str | None = None, typ: str | None = None
):
    req = httpx.Request("POST", "https://api.openai.com/v1/responses")
    return cls("fehler", response=httpx.Response(status, request=req), body={"code": code, "type": typ})


def _guthaben_leer() -> openai.RateLimitError:
    return _api_error(openai.RateLimitError, 429, "credit_balance_exhausted", "insufficient_quota")


def _pdf_mit_text(text: str) -> bytes:
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), text)
        return doc.tobytes()


# ---------- ki_fehler ----------


def test_guthaben_leer_wird_erkannt() -> None:
    from app.services import ki_fehler

    e = _guthaben_leer()
    assert ki_fehler.ist_guthaben_leer(e)
    assert ki_fehler.ist_dauerhaft(e)
    assert "Guthaben" in ki_fehler.nutzer_meldung(e)


def test_normales_ratenlimit_ist_nicht_guthaben_leer() -> None:
    from app.services import ki_fehler

    e = _api_error(openai.RateLimitError, 429, "rate_limit_exceeded", "requests")
    assert not ki_fehler.ist_guthaben_leer(e)
    assert not ki_fehler.ist_dauerhaft(e)
    assert "Ratenlimit" in ki_fehler.nutzer_meldung(e)


def test_unbekannter_fehler_liefert_generische_meldung() -> None:
    from app.services import ki_fehler

    assert ki_fehler.nutzer_meldung(RuntimeError("x")) == ki_fehler.GENERISCHE_MELDUNG
    assert "Modell" in ki_fehler.nutzer_meldung(_api_error(openai.NotFoundError, 404))


async def test_guthaben_push_hoechstens_einmal_taeglich(monkeypatch) -> None:
    from app.services import ki_fehler

    monkeypatch.setattr(ki_fehler, "_letzter_guthaben_push", None)
    push = AsyncMock()
    monkeypatch.setattr(ki_fehler, "notify_failure", push)

    await ki_fehler.melde_ki_fehler(_guthaben_leer())
    await ki_fehler.melde_ki_fehler(_guthaben_leer())
    await ki_fehler.melde_ki_fehler(RuntimeError("kein Guthaben-Fehler"))

    assert push.await_count == 1


# ---------- model_config ----------


def test_model_settings_setzt_reasoning_fuer_gpt5() -> None:
    from app.agents.model_config import model_settings
    from app.config import settings

    ms = model_settings("gpt-5.6-luna", 2000)
    assert ms.max_tokens == 2000
    assert ms.reasoning is not None
    assert ms.reasoning.effort == settings.reasoning_effort
    assert ms.temperature is None  # gpt-5.x unterstützt kein temperature


@pytest.mark.parametrize("model", ["gpt-4.1", "gpt-5.2-chat-latest"])
def test_model_settings_ohne_reasoning_fuer_nicht_reasoning_modelle(model: str) -> None:
    from app.agents.model_config import model_settings

    assert model_settings(model, 500).reasoning is None


def test_chat_completion_limits() -> None:
    from app.agents.model_config import chat_completion_limits

    assert "max_completion_tokens" in chat_completion_limits("gpt-5.6-luna", 100)
    assert "max_tokens" not in chat_completion_limits("o4-mini", 100)
    assert chat_completion_limits("gpt-4.1", 100) == {"max_tokens": 100}


# ---------- Bilder ----------


def _jpeg(size: tuple[int, int], orientation: int | None = None) -> bytes:
    buf = io.BytesIO()
    exif = Image.Exif()
    if orientation:
        exif[0x0112] = orientation
    Image.new("RGB", size, "white").save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


def test_image_data_url_erkennt_format() -> None:
    from app.services.storage_service import image_data_url

    assert image_data_url(_jpeg((10, 10))).startswith("data:image/jpeg;base64,")
    assert image_data_url(b"\x89PNG\r\n\x1a\n" + b"\x00" * 10).startswith("data:image/png;base64,")


def test_grosses_foto_wird_verkleinert() -> None:
    from app.services.storage_service import _MAX_IMAGE_EDGE, _normalize_image

    out = _normalize_image(_jpeg((4000, 1000)))
    with Image.open(io.BytesIO(out)) as img:
        assert img.format == "JPEG"
        assert max(img.size) <= _MAX_IMAGE_EDGE


def test_foto_wird_gemaess_exif_gedreht() -> None:
    from app.services.storage_service import _normalize_image

    out = _normalize_image(_jpeg((200, 100), orientation=6))  # 6 = 90° im Uhrzeigersinn
    with Image.open(io.BytesIO(out)) as img:
        assert img.size == (100, 200)


def test_kleines_bild_und_ungueltige_daten_bleiben_unveraendert() -> None:
    from app.services.storage_service import _normalize_image

    klein = _jpeg((100, 100))
    assert _normalize_image(klein) is klein
    kaputt = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100
    assert _normalize_image(kaputt) is kaputt


# ---------- InvoiceExtraction ----------


def test_zu_lange_freitexte_werden_gekuerzt_statt_verworfen() -> None:
    from app.agents.invoice_agent import InvoiceExtraction

    ex = InvoiceExtraction.model_validate(
        {"purchase_date": "2025-03-14", "amount_eur": 49.99, "produkt_name": "P" * 500, "notes": "N" * 999}
    )
    assert len(ex.produkt_name) == 200
    assert len(ex.notes) == 300
    assert str(ex.purchase_date) == "2025-03-14"


def test_ergaenzt_um_fuellt_nur_leere_felder() -> None:
    from app.agents.invoice_agent import InvoiceExtraction

    vision = InvoiceExtraction(amount_eur=10.0)
    text = InvoiceExtraction(amount_eur=99.0, produkt_name="Kamera")
    merged = vision.ergaenzt_um(text)
    assert merged.amount_eur == 10.0
    assert merged.produkt_name == "Kamera"


# ---------- /api/invoices/analyze ----------


def test_textlayer_ohne_kerndaten_nutzt_vision_fallback(mocker) -> None:
    from app.agents.invoice_agent import InvoiceExtraction

    text_mock = AsyncMock(return_value=InvoiceExtraction(produkt_name="Sigma 85mm"))
    vision_mock = AsyncMock(return_value=InvoiceExtraction(purchase_date="2025-06-01", amount_eur=899.0))
    mocker.patch("app.api.invoices.analyze_invoice_from_text", text_mock)
    mocker.patch("app.api.invoices.analyze_invoice", vision_mock)

    pdf = _pdf_mit_text("Seite 1 von 1")
    r = client.post("/api/invoices/analyze", files={"file": ("scan.pdf", pdf, "application/pdf")})

    assert r.status_code == 200
    data = r.json()
    assert data["purchase_date"] == "2025-06-01"
    assert data["amount_eur"] == 899.0
    assert data["produkt_name"] == "Sigma 85mm"  # aus dem Textlayer ergänzt
    assert vision_mock.await_count == 1


def test_textlayer_mit_kerndaten_ueberspringt_vision(mocker) -> None:
    from app.agents.invoice_agent import InvoiceExtraction

    mocker.patch(
        "app.api.invoices.analyze_invoice_from_text",
        AsyncMock(return_value=InvoiceExtraction(purchase_date="2025-01-02", amount_eur=5.0)),
    )
    vision_mock = AsyncMock()
    mocker.patch("app.api.invoices.analyze_invoice", vision_mock)

    pdf = _pdf_mit_text("Rechnungsdatum 02.01.2025 Summe 5,00 EUR")
    r = client.post("/api/invoices/analyze", files={"file": ("r.pdf", pdf, "application/pdf")})

    assert r.status_code == 200
    assert r.json()["purchase_date"] == "2025-01-02"
    vision_mock.assert_not_awaited()


def test_textlayer_fehler_faellt_auf_vision_zurueck(mocker) -> None:
    from app.agents.invoice_agent import InvoiceExtraction

    mocker.patch("app.api.invoices.analyze_invoice_from_text", AsyncMock(side_effect=ValueError("kaputt")))
    mocker.patch(
        "app.api.invoices.analyze_invoice", AsyncMock(return_value=InvoiceExtraction(amount_eur=12.5))
    )

    pdf = _pdf_mit_text("Rechnung")
    r = client.post("/api/invoices/analyze", files={"file": ("r.pdf", pdf, "application/pdf")})

    assert r.status_code == 200
    assert r.json()["amount_eur"] == 12.5


def test_leeres_guthaben_liefert_502_mit_klarer_meldung(mocker) -> None:
    """Früher: 200 mit leeren Feldern. Jetzt: 502 mit Hinweis aufs Guthaben, ohne Vision-Versuch."""
    mocker.patch("app.api.invoices.analyze_invoice_from_text", AsyncMock(side_effect=_guthaben_leer()))
    vision_mock = AsyncMock()
    mocker.patch("app.api.invoices.analyze_invoice", vision_mock)
    mocker.patch("app.services.ki_fehler.notify_failure", AsyncMock())

    pdf = _pdf_mit_text("Rechnung")
    r = client.post("/api/invoices/analyze", files={"file": ("r.pdf", pdf, "application/pdf")})

    assert r.status_code == 502
    assert "Guthaben" in r.json()["detail"]
    vision_mock.assert_not_awaited()


def test_vision_fehler_bei_foto_liefert_502(mocker) -> None:
    mocker.patch("app.api.invoices.analyze_invoice", AsyncMock(side_effect=_guthaben_leer()))
    mocker.patch("app.services.ki_fehler.notify_failure", AsyncMock())

    r = client.post("/api/invoices/analyze", files={"file": ("beleg.jpg", _jpeg((50, 50)), "image/jpeg")})

    assert r.status_code == 502
    assert "Guthaben" in r.json()["detail"]


# ---------- Rechnung speichern ----------


def test_rechnung_uebernimmt_kaufdatum_ins_produkt() -> None:
    r = client.post("/api/products", json={"name": "Kaufdatum-Test", "kategorie": "Elektronik"})
    product_id = r.json()["id"]

    pdf = _pdf_mit_text("Beleg")
    r = client.post(
        "/api/invoices",
        data={"product_id": str(product_id), "purchase_date": "2025-03-14"},
        files={"file": ("beleg.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 201
    assert client.get(f"/api/products/{product_id}").json()["purchase_date"] == "2025-03-14"

    # Vorhandenes Kaufdatum wird nicht überschrieben
    r = client.post(
        "/api/invoices",
        data={"product_id": str(product_id), "purchase_date": "2026-01-01"},
        files={"file": ("beleg2.pdf", pdf, "application/pdf")},
    )
    assert client.get(f"/api/products/{product_id}").json()["purchase_date"] == "2025-03-14"
    client.delete(f"/api/products/{product_id}")


# ---------- QA-Agent: Produkte/Belege ----------


def test_list_products_enthaelt_belege() -> None:
    from app.agents.qa_agent import _list_products_sync

    r = client.post(
        "/api/products",
        json={"name": "Chat-Testgerät", "kategorie": "Elektronik", "warranty_end": "2027-05-01"},
    )
    product_id = r.json()["id"]
    client.post(
        "/api/invoices",
        data={"product_id": str(product_id), "purchase_date": "2025-05-01", "amount_eur": "249.0"},
        files={"file": ("b.pdf", _pdf_mit_text("Beleg"), "application/pdf")},
    )

    produkte = {p["name"]: p for p in json.loads(_list_products_sync())}
    p = produkte["Chat-Testgerät"]
    assert p["garantie_bis"] == "2027-05-01"
    assert p["kaufdatum"] == "2025-05-01"
    assert p["belege"][0]["betrag_eur"] == 249.0
    client.delete(f"/api/products/{product_id}")


# ---------- OCR ----------


@pytest.fixture()
def zweiseitiger_scan(tmp_path, monkeypatch):
    from app.config import settings

    monkeypatch.setattr(settings, "data_dir", tmp_path)
    monkeypatch.setattr(settings, "model_fast", "gpt-5.6-luna")
    docs = tmp_path / "documents"
    docs.mkdir(parents=True)
    pdf_path = docs / "scan.pdf"
    with pymupdf.open() as doc:
        doc.new_page()
        doc.new_page()
        doc.save(str(pdf_path))
    return pdf_path


def _fake_client(create: AsyncMock) -> MagicMock:
    fake = MagicMock()
    fake.chat.completions.create = create
    return fake


async def test_ocr_nutzt_max_completion_tokens(zweiseitiger_scan) -> None:
    from app.services import embedding_service

    create = AsyncMock(
        return_value=SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="Text"))])
    )
    with patch.object(embedding_service, "_client", return_value=_fake_client(create)):
        await embedding_service.ocr_document_text(str(zweiseitiger_scan))

    kwargs = create.call_args.kwargs
    assert "max_completion_tokens" in kwargs
    assert "max_tokens" not in kwargs  # von Reasoning-Modellen abgelehnt


async def test_ocr_bricht_bei_leerem_guthaben_ab(zweiseitiger_scan) -> None:
    from app.services import embedding_service

    create = AsyncMock(side_effect=_guthaben_leer())
    with (
        patch.object(embedding_service, "_client", return_value=_fake_client(create)),
        pytest.raises(openai.RateLimitError),
    ):
        await embedding_service.ocr_document_text(str(zweiseitiger_scan))

    assert create.await_count == 1  # zweite Seite wird nicht mehr versucht
