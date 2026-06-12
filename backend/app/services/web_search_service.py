"""Web-Suchdienst mit austauschbarem Provider (Serper ↔ Brave).

Aktuell implementiert: Serper (https://serper.dev)
Zum Wechsel auf Brave: SEARCH_PROVIDER=brave in .env setzen.
"""
from __future__ import annotations

import logging
from typing import Protocol

import httpx
from pydantic import BaseModel

log = logging.getLogger(__name__)

_MAX_RESULTS = 5
_TIMEOUT_S = 10.0
_MAX_TITLE_CHARS = 200
_MAX_SNIPPET_CHARS = 500
_MAX_URL_CHARS = 500


class SearchResult(BaseModel):
    title: str
    snippet: str
    url: str


def _make_result(title: str, snippet: str, url: str) -> SearchResult:
    """Baut ein längenbegrenztes SearchResult; nur http(s)-URLs werden übernommen."""
    if not url.startswith(("http://", "https://")):
        url = ""
    return SearchResult(
        title=title[:_MAX_TITLE_CHARS],
        snippet=snippet[:_MAX_SNIPPET_CHARS],
        url=url[:_MAX_URL_CHARS],
    )


# ---------------------------------------------------------------------------
# Provider-Protokoll
# ---------------------------------------------------------------------------

class SearchProvider(Protocol):
    async def search(self, query: str) -> list[SearchResult]:
        ...


# ---------------------------------------------------------------------------
# Serper
# ---------------------------------------------------------------------------

class SerperSearchService:
    """Google-Suche via Serper API (https://serper.dev).

    API-Docs: https://serper.dev/api-reference
    """

    _URL = "https://google.serper.dev/search"

    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._transport = transport

    async def search(self, query: str) -> list[SearchResult]:
        headers = {"X-API-KEY": self._api_key, "Content-Type": "application/json"}
        payload = {"q": query, "num": _MAX_RESULTS, "gl": "de", "hl": "de"}

        async with httpx.AsyncClient(timeout=_TIMEOUT_S, transport=self._transport) as client:
            resp = await client.post(self._URL, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        return [
            _make_result(item.get("title", ""), item.get("snippet", ""), item.get("link", ""))
            for item in data.get("organic", [])[:_MAX_RESULTS]
        ]


# ---------------------------------------------------------------------------
# Brave
# ---------------------------------------------------------------------------

class BraveSearchService:
    """Brave Search API (https://brave.com/search/api/).

    Zum Aktivieren: SEARCH_PROVIDER=brave, SEARCH_API_KEY=<brave-key> in .env.
    API-Docs: https://api.search.brave.com/app/documentation/web-search
    """

    _URL = "https://api.search.brave.com/res/v1/web/search"

    def __init__(self, api_key: str, transport: httpx.AsyncBaseTransport | None = None) -> None:
        self._api_key = api_key
        self._transport = transport

    async def search(self, query: str) -> list[SearchResult]:
        headers = {
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": self._api_key,
        }
        params = {"q": query, "count": _MAX_RESULTS, "country": "de", "search_lang": "de"}

        async with httpx.AsyncClient(timeout=_TIMEOUT_S, transport=self._transport) as client:
            resp = await client.get(self._URL, headers=headers, params=params)
            resp.raise_for_status()

        data = resp.json()
        return [
            _make_result(item.get("title", ""), item.get("description", ""), item.get("url", ""))
            for item in data.get("web", {}).get("results", [])[:_MAX_RESULTS]
        ]


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_search_service(provider: str, api_key: str) -> SearchProvider:
    """Gibt den konfigurierten Such-Provider zurück.

    provider: "serper" | "brave"
    """
    if provider == "brave":
        return BraveSearchService(api_key)
    if provider == "serper":
        return SerperSearchService(api_key)
    raise ValueError(f"Unbekannter SEARCH_PROVIDER: {provider!r}. Erlaubt: serper, brave")
