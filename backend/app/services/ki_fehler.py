"""Übersetzt Fehler der OpenAI-API in verständliche Meldungen für die Oberfläche.

Hintergrund: Ein aufgebrauchtes OpenAI-Guthaben ließ tagelang jede KI-Analyse
still leer zurückkommen. Solche Fehler sollen sofort sichtbar sein — als
konkrete Meldung im Frontend und (höchstens einmal täglich) als Push.
"""
from __future__ import annotations

import logging
import time

import openai

from app.services.pushover_service import notify_failure

log = logging.getLogger(__name__)

GENERISCHE_MELDUNG = "KI-Analyse fehlgeschlagen. Details siehe Server-Log."

# Fehler-Codes der OpenAI-API für "kein Guthaben mehr"
_GUTHABEN_CODES = {"insufficient_quota", "credit_balance_exhausted"}
_GUTHABEN_PUSH_ABSTAND_S = 24 * 3600
_letzter_guthaben_push: float | None = None


def ist_guthaben_leer(exc: BaseException) -> bool:
    """True, wenn die OpenAI-API wegen aufgebrauchten Guthabens abgelehnt hat."""
    if not isinstance(exc, openai.RateLimitError):
        return False
    return bool({getattr(exc, "code", None), getattr(exc, "type", None)} & _GUTHABEN_CODES)


def ist_dauerhaft(exc: BaseException) -> bool:
    """True bei Fehlern, die sich durch Wiederholen nicht beheben (Guthaben, Key, Modell)."""
    return ist_guthaben_leer(exc) or isinstance(exc, openai.AuthenticationError | openai.NotFoundError)


def nutzer_meldung(exc: BaseException) -> str:
    """Kurze, handlungsleitende Fehlermeldung für das Frontend (ohne interne Details)."""
    if ist_guthaben_leer(exc):
        return (
            "OpenAI-Guthaben aufgebraucht — bitte unter platform.openai.com "
            "→ Settings → Billing aufladen."
        )
    if isinstance(exc, openai.AuthenticationError):
        return "OpenAI-API-Key ungültig oder fehlt (OPENAI_API_KEY in .env prüfen)."
    if isinstance(exc, openai.RateLimitError):
        return "OpenAI-Ratenlimit erreicht — bitte in einer Minute erneut versuchen."
    if isinstance(exc, openai.NotFoundError):
        return "KI-Modell nicht verfügbar — Modellnamen (MODEL_*) in .env prüfen."
    if isinstance(exc, openai.APIConnectionError):
        return "OpenAI nicht erreichbar — Internetverbindung prüfen."
    return GENERISCHE_MELDUNG


async def melde_ki_fehler(exc: BaseException) -> str:
    """Schickt bei leerem Guthaben (max. einmal täglich) einen Push und gibt die Nutzer-Meldung zurück.

    Das Loggen des Fehlers (mit Traceback) bleibt Aufgabe des Aufrufers.
    """
    global _letzter_guthaben_push
    if ist_guthaben_leer(exc):
        jetzt = time.monotonic()
        if _letzter_guthaben_push is None or jetzt - _letzter_guthaben_push > _GUTHABEN_PUSH_ABSTAND_S:
            _letzter_guthaben_push = jetzt
            await notify_failure(
                "⚠ OpenAI-Guthaben aufgebraucht",
                "Alle KI-Funktionen (Dokument-/Rechnungsanalyse, Chat, Empfehlungen) schlagen fehl, "
                "bis das Guthaben unter platform.openai.com → Billing aufgeladen ist.",
            )
    return nutzer_meldung(exc)
