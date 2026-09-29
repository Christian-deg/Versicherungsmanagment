"""Chat-Endpoint."""
from __future__ import annotations

import logging

from agents.exceptions import InputGuardrailTripwireTriggered, OutputGuardrailTripwireTriggered
from fastapi import APIRouter, HTTPException, status

from app.agents.qa_agent import ask
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services import ki_fehler

log = logging.getLogger(__name__)
router = APIRouter()


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    try:
        result = await ask(req.frage, [(m.rolle, m.text) for m in req.verlauf])
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
        # Interne Fehlerdetails nur ins Log — ans Frontend nur eine verständliche Meldung
        log.exception("Chat fehlgeschlagen")
        meldung = await ki_fehler.melde_ki_fehler(e)
        if meldung == ki_fehler.GENERISCHE_MELDUNG:
            meldung = "Chat fehlgeschlagen. Details siehe Server-Log."
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=meldung) from e
    return ChatResponse(antwort=result.antwort, quellen=result.quellen, konfidenz=result.konfidenz)
