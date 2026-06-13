"""Gemeinsames Websuch-Tool für QA- und Empfehlungs-Agent.

Liegt bewusst in einem eigenen Modul, damit beide Agenten dasselbe Tool nutzen,
ohne sich gegenseitig zu importieren. Enthält die technischen Guardrails
(Sensitive-Data-Check der Anfrage, Injection-Filter der Treffer).
"""
from __future__ import annotations

import json
import logging

from agents import function_tool

from app.agents.guardrails import detect_injection, detect_sensitive
from app.config import settings
from app.services.web_search_service import get_search_service

log = logging.getLogger(__name__)

_MAX_QUERY_CHARS = 200


async def run_web_search(query: str) -> str:
    """Eigentliche Such-Logik (vom Tool-Decorator getrennt, damit testbar).

    Technische Guardrails — die Prompt-Anweisung allein ist keine Kontrolle:
    - LLM02: Query wird vor dem Versand an den externen Dienst auf sensible
      Daten geprüft und längenbegrenzt.
    - LLM01: Treffer mit Prompt-Injection-Mustern in Titel/Snippet werden
      verworfen, bevor sie in den Modell-Kontext gelangen.
    """
    if not settings.search_api_key:
        return json.dumps({"error": "SEARCH_API_KEY nicht konfiguriert."})

    query = query.strip()[:_MAX_QUERY_CHARS]
    if not query:
        return json.dumps({"error": "Leere Suchanfrage."})
    found = detect_sensitive(query)
    if found:
        log.warning("web_search blockiert: %s in Suchanfrage erkannt", found)
        return json.dumps({"error": "Suchanfrage enthält sensible Daten und wurde blockiert."})

    try:
        svc = get_search_service(settings.search_provider, settings.search_api_key)
        results = await svc.search(query)
    except Exception as exc:  # noqa: BLE001
        log.warning("web_search fehlgeschlagen: %s", exc)
        return json.dumps({"error": "Websuche nicht verfügbar."})

    safe_results = []
    for r in results:
        if detect_injection(f"{r.title} {r.snippet}"):
            log.warning("web_search: Treffer mit Injection-Pattern verworfen (%s)", r.url[:100])
            continue
        safe_results.append({"title": r.title, "snippet": r.snippet, "url": r.url})
    return json.dumps(safe_results, ensure_ascii=False)


@function_tool
async def web_search(query: str) -> str:
    """Sucht im Web nach aktuellen Versicherungstarifen, -vergleichen und Marktinfos.

    Maximal 5 Treffer. Gibt Titel, Snippet und URL zurück.
    Nur für sachliche Marktinformationen nutzen – keine persönlichen Daten übergeben.
    """
    return await run_web_search(query)
