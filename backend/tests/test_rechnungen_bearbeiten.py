"""Tests für die nachträgliche Korrektur von Rechnungen (PATCH /api/invoices/{id})."""
from __future__ import annotations

from datetime import date, timedelta

import pymupdf
import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


@pytest.fixture(scope="module", autouse=True)
def _setup_db() -> None:
    from app.models.database import init_db

    init_db()


@pytest.fixture()
def rechnung_ohne_daten():
    """Produkt ohne Kaufdatum/Garantie + Rechnung ohne Kaufdatum und Betrag."""
    r = client.post("/api/products", json={"name": "Korrektur-Test", "kategorie": "Audio"})
    product_id = r.json()["id"]
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "Beleg")
        pdf = doc.tobytes()
    r = client.post(
        "/api/invoices",
        data={"product_id": str(product_id), "notes": "alte Notiz"},
        files={"file": ("beleg.pdf", pdf, "application/pdf")},
    )
    assert r.status_code == 201
    yield product_id, r.json()
    client.delete(f"/api/products/{product_id}")


def test_vergessenen_betrag_nachtragen(rechnung_ohne_daten) -> None:
    _, inv = rechnung_ohne_daten
    r = client.patch(f"/api/invoices/{inv['id']}", json={"amount_eur": 149.0})

    assert r.status_code == 200
    data = r.json()
    assert data["amount_eur"] == 149.0
    # Nicht mitgeschickte Felder bleiben unverändert
    assert data["notes"] == "alte Notiz"
    assert data["purchase_date"] is None
    assert data["retain_until"] == inv["retain_until"]


def test_kaufdatum_korrigieren_berechnet_frist_neu(rechnung_ohne_daten) -> None:
    product_id, inv = rechnung_ohne_daten
    kauf = date(2026, 5, 19)
    r = client.patch(f"/api/invoices/{inv['id']}", json={"purchase_date": kauf.isoformat()})

    assert r.status_code == 200
    assert r.json()["retain_until"] == (kauf + timedelta(days=730)).isoformat()
    # Fehlendes Produkt-Kaufdatum wird ergänzt
    assert client.get(f"/api/products/{product_id}").json()["purchase_date"] == kauf.isoformat()


def test_explizites_null_leert_feld(rechnung_ohne_daten) -> None:
    _, inv = rechnung_ohne_daten
    r = client.patch(f"/api/invoices/{inv['id']}", json={"notes": None})
    assert r.status_code == 200
    assert r.json()["notes"] is None


def test_ungueltiger_betrag_wird_abgelehnt(rechnung_ohne_daten) -> None:
    _, inv = rechnung_ohne_daten
    assert client.patch(f"/api/invoices/{inv['id']}", json={"amount_eur": -5}).status_code == 422


def test_laengere_garantie_verlaengert_aufbewahrung_nie_kuerzer(rechnung_ohne_daten) -> None:
    product_id, inv = rechnung_ohne_daten
    produkt = client.get(f"/api/products/{product_id}").json()
    for k in ("id", "created_at"):
        produkt.pop(k)

    lang = (date.fromisoformat(inv["retain_until"]) + timedelta(days=400)).isoformat()
    client.put(f"/api/products/{product_id}", json={**produkt, "warranty_end": lang})
    assert client.get(f"/api/invoices/{inv['id']}").json()["retain_until"] == lang

    # Kürzeres Garantieende verkürzt die Aufbewahrung nicht
    kurz = date.today().isoformat()
    client.put(f"/api/products/{product_id}", json={**produkt, "warranty_end": kurz})
    assert client.get(f"/api/invoices/{inv['id']}").json()["retain_until"] == lang


def test_unbekannte_rechnung_404() -> None:
    assert client.patch("/api/invoices/999999", json={"amount_eur": 1.0}).status_code == 404
