"""Chat-Endpoint."""
from __future__ import annotations

import logging

from agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from fastapi import APIRouter, HTTPException, status

from app.agents.qa_agent import ask
from app.schemas.schemas import ChatRequest, ChatResponse

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = await ask(req.frage)
    except InputGuardrailTripwireTriggered as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Anfrage wurde vom Sicherheitsfilter abgelehnt.",
        ) from e
    except OutputGuardrailTripwireTriggered as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Antwort wurde vom Sicherheitsfilter blockiert.",
        ) from e
    except Exception as e:
        # Interne Fehlerdetails nur ins Log — nicht an den Client leaken
        log.exception("Chat fehlgeschlagen")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Chat fehlgeschlagen. Details siehe Server-Log.",
        ) from e
    return ChatResponse(antwort=result.antwort, quellen=result.quellen, konfidenz=result.konfidenz)
