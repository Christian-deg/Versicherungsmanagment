"""Smoke-Test aller KI-Funktionen gegen die echte OpenAI-API.

Die Unit-Tests ersetzen alle Agenten durch Attrappen — falsche Modellnamen,
abgelehnte API-Parameter, zu knappe Token-Limits oder ein leeres Guthaben
fallen dort nicht auf. Dieser Test ruft jede KI-Funktion einmal mit
synthetischen Daten auf (Kosten: wenige Cent + eine Websuche).

Aufruf im laufenden Container (nach jedem Modell-/SDK-Wechsel):
    docker exec versicherungs_backend /app/.venv/bin/python -m app.smoke_test

Schreibt nichts in DB oder Suchindex. Exit-Code 1, wenn ein Check fehlschlägt.
"""
from __future__ import annotations

import asyncio
import logging
import sys
import time
import uuid
from collections.abc import Awaitable, Callable

import pymupdf
from agents import Runner

from app.config import settings
from app.services import ki_fehler

_BELEG = """MediaMarkt Berlin-Alexanderplatz
Rechnung Nr. 2025-4711
Rechnungsdatum: 14.03.2025
1x Sony WH-1000XM5 Kopfhoerer schwarz      349,00 EUR
Summe (inkl. 19% MwSt.)                    349,00 EUR
2 Jahre Herstellergarantie
"""

_POLICE = """Allianz Versicherungs-AG
Versicherungsschein Hausratversicherung
Versicherungsscheinnummer: HR-123456789
Versicherungsbeginn: 01.01.2025   Ablauf: 01.01.2026
Jahresbeitrag: 120,00 EUR, zahlbar jaehrlich
Kuendigung: 3 Monate vor Ablauf zum 01.01.
"""


def _render_png(text: str) -> bytes:
    """Rendert Text als Bild — simuliert einen Scan ohne Textlayer."""
    with pymupdf.open() as doc:
        page = doc.new_page()
        page.insert_text((72, 72), text, fontsize=11)
        return page.get_pixmap(dpi=150).tobytes("png")


async def _embedding() -> str:
    from app.services.embedding_service import _client

    resp = await _client().embeddings.create(model=settings.model_embedding, input=["Test"])
    return f"Dimension {len(resp.data[0].embedding)}"


async def _klassifizierer() -> str:
    # Agent direkt aufrufen: classify_document ist fail-open und würde Fehler verdecken
    from app.agents.classifier_agent import DokumentTyp, Klassifikation, _classifier_text_agent

    run = await Runner.run(_classifier_text_agent, input=f"<dokument>\n{_BELEG}\n</dokument>")
    r = run.final_output_as(Klassifikation)
    assert r.typ == DokumentTyp.RECHNUNG, f"erkannt als '{r.typ.value}' statt 'rechnung'"
    return f"typ={r.typ.value}"


def _pruefe_beleg(r) -> str:
    assert str(r.purchase_date) == "2025-03-14", f"Kaufdatum {r.purchase_date} statt 2025-03-14"
    assert r.amount_eur == 349.0, f"Betrag {r.amount_eur} statt 349.0"
    return f"{r.purchase_date}, {r.amount_eur} EUR, {r.produkt_name}, Garantie {r.garantie_monate} Mon."


async def _rechnung_text() -> str:
    from app.agents.invoice_agent import analyze_invoice_from_text

    return _pruefe_beleg(await analyze_invoice_from_text(_BELEG))


async def _rechnung_vision() -> str:
    from app.agents.invoice_agent import analyze_invoice

    return _pruefe_beleg(await analyze_invoice([_render_png(_BELEG)]))


async def _police_vision() -> str:
    from app.agents.document_agent import analyze_document

    r = await analyze_document([_render_png(_POLICE)], "police.png")
    assert "123456789" in r.vertragsnummer, f"Vertragsnummer '{r.vertragsnummer}'"
    return f"{r.versicherer}, {r.kategorie.value}, {r.start_date}–{r.end_date}, {r.praemie_eur} EUR"


async def _ocr() -> str:
    from app.services import embedding_service

    incoming = settings.documents_dir.resolve() / "_incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    path = incoming / f"_smoke_{uuid.uuid4().hex}.png"
    path.write_bytes(_render_png(_POLICE))
    try:
        text = await embedding_service.ocr_document_text(str(path))
    finally:
        path.unlink(missing_ok=True)
    assert "123456789" in text, "OCR lieferte keinen/falschen Text (Details im Log)"
    return f"{len(text)} Zeichen"


async def _chat() -> str:
    from app.agents.qa_agent import ask

    r = await ask("Wie viele Versicherungen und wie viele Produkte habe ich erfasst? Ein Satz.")
    return f"[{r.konfidenz.value}] {r.antwort[:90]}"


async def _empfehlung() -> str:
    from app.agents.recommendation_agent import evaluate

    r = await evaluate(
        "insurance_id: 0\nKategorie: Haftpflicht\nVersicherer: Testversicherer\n"
        "Laufzeit: 2025-01-01 bis 2026-01-01\nZahlungsintervall: jährlich\n"
        "Prämie pro Jahr (EUR): 70\nKündigung: nicht angegeben\nNotizen: -\n"
    )
    return f"[{r.handlungsbedarf.value}] {r.hinweis[:90]}"


CHECKS: list[tuple[str, str, Callable[[], Awaitable[str]]]] = [
    ("Embedding", settings.model_embedding, _embedding),
    ("Klassifizierer", settings.model_fast, _klassifizierer),
    ("Rechnung (Text)", settings.model_fast, _rechnung_text),
    ("Rechnung (Vision)", settings.model_document, _rechnung_vision),
    ("Police + Evaluator", settings.model_document, _police_vision),
    ("OCR", settings.model_fast, _ocr),
    ("Chat (RAG)", settings.model_chat, _chat),
    ("Empfehlung", settings.model_chat, _empfehlung),
]


async def main() -> int:
    logging.basicConfig(level=logging.ERROR, format="    log: %(name)s | %(message)s")
    print(f"Reasoning-Aufwand: {settings.reasoning_effort}\n")
    fehler = 0
    for name, model, check in CHECKS:
        t0 = time.monotonic()
        try:
            info = await check()
            print(f"OK    {name:<20} {model:<24} {time.monotonic() - t0:5.1f}s  {info}")
        except Exception as e:  # noqa: BLE001
            fehler += 1
            grund = str(e) if isinstance(e, AssertionError) else ki_fehler.nutzer_meldung(e)
            if grund == ki_fehler.GENERISCHE_MELDUNG:
                grund = f"{type(e).__name__}: {str(e)[:300]}"
            print(f"FEHLER {name:<19} {model:<24} {time.monotonic() - t0:5.1f}s  {grund}")
            if ki_fehler.ist_dauerhaft(e):
                print("\nDauerhafter API-Fehler — weitere Checks übersprungen.")
                break
    print(f"\n{fehler} Check(s) fehlgeschlagen." if fehler else f"\nAlle {len(CHECKS)} Checks bestanden.")
    return 1 if fehler else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
