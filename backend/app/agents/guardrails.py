"""Gemeinsame Guardrails für alle Agenten (siehe SKILL.md)."""
from __future__ import annotations

import re
from typing import Any

from agents import GuardrailFunctionOutput, RunContextWrapper
from pydantic import BaseModel

# LLM01 — Prompt-Injection-Patterns (regex, kein LLM)
INJECTION_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        r"ignore\s+(previous|all|above)\s+instructions",
        r"disregard\s+(previous|all|above)",
        r"system\s*:\s*you\s+are",
        r"<\|.*?\|>",
        r"important:?\s*new\s*instructions",
        r"forget\s+everything",
        r"reveal\s+your\s+system\s+prompt",
        # Deutsche Varianten
        r"ignoriere\s+(alle?\s+)?(vorherigen?\s+)?(anweisungen|instruktionen)",
        r"vergiss\s+(alles|alle\s+vorherigen\s+anweisungen)",
        r"zeige?\s+(deinen?\s+)?system(-|\s*)prompt",
        r"neue\s+instruktionen\s*:",
        r"neue\s+anweisungen\s*:",
    )
)

# LLM02 — Sensitive-Info-Patterns (für Freitext-Felder im Output-Guardrail)
SENSITIVE_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "IP-Adresse"),
    (re.compile(r"password|api[_-]?key|secret[_-]?key|bearer\s+\w+", re.IGNORECASE), "Credential"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "OpenAI-Key"),
    (re.compile(r"/home/\w|/root/|C:\\Users\\", re.IGNORECASE), "absoluter Systempfad"),
)


class GuardrailResult(BaseModel):
    ist_valide: bool
    grund: str | None = None


def detect_injection(text: str) -> str | None:
    """Gibt das gefundene Pattern zurück, oder None."""
    for pat in INJECTION_PATTERNS:
        if pat.search(text):
            return pat.pattern
    return None


def detect_sensitive(text: str) -> str | None:
    """Gibt die Bezeichnung der gefundenen Sensitive-Info zurück, oder None."""
    for pat, name in SENSITIVE_PATTERNS:
        if pat.search(text):
            return name
    return None


async def injection_input_guardrail(
    ctx: RunContextWrapper[Any],
    agent: Any,
    input_data: Any,
) -> GuardrailFunctionOutput:
    """Generischer Input-Guardrail gegen Prompt-Injection."""
    text = input_data if isinstance(input_data, str) else str(input_data)
    found = detect_injection(text)
    if found:
        return GuardrailFunctionOutput(
            output_info=GuardrailResult(ist_valide=False, grund=f"Prompt-Injection erkannt: {found}"),
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info=GuardrailResult(ist_valide=True), tripwire_triggered=False)


def check_freetext_fields(output: BaseModel, freetext_fields: list[str]) -> str | None:
    """Prüft Freitext-Felder eines Outputs auf Sensitive-Info. Gibt Fehler zurück oder None."""
    for fname in freetext_fields:
        val = getattr(output, fname, None)
        if isinstance(val, str) and val:
            found = detect_sensitive(val)
            if found:
                return f"{found} in Feld '{fname}' erkannt"
    return None
