"""Brave Search adapter implementing the WebSearch protocol.

Backs the agentic web-lookup gatherer. The API key is read from settings
(``BRAVE_API_KEY``), never hard-coded.
"""

from __future__ import annotations

from typing import Any

import httpx

from finance_api.classification.gatherers.web_lookup import SearchResult
from finance_api.core.config import settings


class BraveWebSearch:
    """Web search via the Brave Search API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        count: int = 5,
        timeout: float = 15.0,
    ) -> None:
        self._api_key = api_key if api_key is not None else settings.brave_api_key
        self._base_url = base_url or settings.brave_base_url
        self._count = count
        self._timeout = timeout

    @staticmethod
    def _parse(data: dict[str, Any]) -> list[SearchResult]:
        results = (data.get("web") or {}).get("results") or []
        return [
            SearchResult(
                title=r.get("title", ""),
                url=r.get("url", ""),
                snippet=r.get("description", ""),
            )
            for r in results
        ]

    def search(self, query: str) -> list[SearchResult]:
        response = httpx.get(
            self._base_url,
            params={"q": query, "count": self._count},
            headers={
                "X-Subscription-Token": self._api_key,
                "Accept": "application/json",
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        return self._parse(response.json())
