"""Pushover Push-Notification Service."""
from __future__ import annotations

import logging

import httpx

from app.config import settings

log = logging.getLogger(__name__)

PUSHOVER_URL = "https://api.pushover.net/1/messages.json"


class PushoverError(RuntimeError):
    pass


async def send_push(
    title: str,
    message: str,
    priority: int = 0,
    url: str | None = None,
    url_title: str | None = None,
) -> None:
    """Sendet eine Push-Nachricht via Pushover.

    priority:
      -2 = silent, -1 = quiet, 0 = normal, 1 = high (bypass quiet hours), 2 = emergency
    """
    if not settings.pushover_user_key or not settings.pushover_app_token:
        raise PushoverError("Pushover-Keys nicht konfiguriert (PUSHOVER_USER_KEY/APP_TOKEN)")

    if priority not in (-2, -1, 0, 1, 2):
        raise PushoverError(f"Ungültige Priorität: {priority}")

    payload = {
        "token": settings.pushover_app_token,
        "user": settings.pushover_user_key,
        "title": title[:250],
        "message": message[:1024],
        "priority": priority,
    }
    if url:
        payload["url"] = url[:512]
    if url_title:
        payload["url_title"] = url_title[:100]

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(PUSHOVER_URL, data=payload)

    if resp.status_code != 200:
        raise PushoverError(f"Pushover-Fehler {resp.status_code}: {resp.text[:200]}")
    log.info("Pushover gesendet: '%s' (priority=%d)", title, priority)
