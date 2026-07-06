"""Erinnerungs-Verlauf und Pushover-Test."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.config import settings
from app.models.database import get_db
from app.models.models import Notification
from app.schemas.schemas import NotificationRead
from app.services.pushover_service import PushoverError, send_push

log = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[NotificationRead])
def list_notifications(limit: int = 100, db: Session = Depends(get_db)) -> list[Notification]:
    """Letzte Erinnerungen (neueste zuerst) — macht das Warnsystem in der UI nachvollziehbar."""
    limit = max(1, min(500, limit))
    return (
        db.query(Notification)
        .order_by(Notification.trigger_date.desc(), Notification.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/test")
async def send_test_push() -> dict[str, str]:
    """Sendet eine Test-Benachrichtigung, um die Pushover-Konfiguration zu prüfen.

    So fällt ein Konfigurationsfehler sofort auf — nicht erst, wenn eine
    echte Frist-Warnung verloren geht.
    """
    if not settings.pushover_user_key or not settings.pushover_app_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pushover ist nicht konfiguriert (PUSHOVER_USER_KEY / PUSHOVER_APP_TOKEN in .env setzen).",
        )
    try:
        await send_push(
            title="✅ Test-Benachrichtigung",
            message="Pushover funktioniert — der Versicherungs-Assistent kann dich erreichen.",
        )
    except PushoverError as e:
        log.warning("Pushover-Test fehlgeschlagen: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Pushover-Test fehlgeschlagen: {e}",
        ) from e
    return {"status": "ok"}
