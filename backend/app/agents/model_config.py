"""Gemeinsame Modell-Einstellungen für alle KI-Aufrufe.

Zwei Fallen der gpt-5.x-Modelle, die hier zentral abgefangen werden:

- `temperature` wird nicht unterstützt (Aufruf schlägt fehl) — wird nie gesetzt.
- Reasoning-Tokens zählen gegen das Token-Limit. Ohne explizite Reasoning-
  Einstellung gilt der Server-Default des Modells (gpt-5.6-*: medium). Ein
  knappes Limit wird dann vom Reasoning aufgebraucht, die Antwort bricht ab und
  das strukturierte JSON ist ungültig — der gesamte Output geht verloren.

Deshalb setzen alle Agenten den Reasoning-Aufwand explizit (settings.reasoning_effort)
und ein Token-Limit mit genug Luft für Reasoning + Antwort.
"""
from __future__ import annotations

import re

from agents import ModelSettings
from openai.types.shared import Reasoning

from app.config import settings

_O_SERIES = re.compile(r"^o\d")


def is_reasoning_model(model: str) -> bool:
    """gpt-5.x und o-Serie sind Reasoning-Modelle — außer den *-chat-latest-Aliasen."""
    if model.endswith("-chat-latest"):
        return False
    return model.startswith("gpt-5") or bool(_O_SERIES.match(model))


def model_settings(model: str, max_tokens: int) -> ModelSettings:
    """ModelSettings für das Agents SDK: Token-Limit + expliziter Reasoning-Aufwand."""
    reasoning = Reasoning(effort=settings.reasoning_effort) if is_reasoning_model(model) else None
    return ModelSettings(max_tokens=max_tokens, reasoning=reasoning)


def chat_completion_limits(model: str, max_tokens: int) -> dict:
    """Parameter für direkte Chat-Completions-Aufrufe.

    Reasoning-Modelle lehnen `max_tokens` ab — dort gilt `max_completion_tokens`
    (umfasst Reasoning- und Antwort-Tokens).
    """
    if is_reasoning_model(model):
        return {"max_completion_tokens": max_tokens, "reasoning_effort": settings.reasoning_effort}
    return {"max_tokens": max_tokens}
