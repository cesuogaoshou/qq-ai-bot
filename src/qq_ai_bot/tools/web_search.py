from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchClient(Protocol):
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        ...


class SearchDisabledError(RuntimeError):
    pass


class DisabledWebSearchClient:
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        raise SearchDisabledError("Web search is disabled")


class TavilySearchClient:
    def __init__(
        self,
        *,
        http: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        timeout: float = 15.0,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        try:
            response = await self._http.post(
                f"{self._base_url}/search",
                json={
                    "query": query,
                    "search_depth": "basic",
                    "max_results": max_results,
                },
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
            if response.status_code >= 400:
                logger.warning(
                    "Tavily search failed: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
                return []
            data = response.json()
        except httpx.TimeoutException:
            logger.warning("Tavily search timed out")
            return []
        except httpx.HTTPError as exc:
            logger.warning("Tavily search failed: error=%s", exc.__class__.__name__)
            return []

        results = []
        for item in data.get("results", []):
            title = item.get("title", "")
            url = item.get("url", "")
            snippet = item.get("content", "") or item.get("snippet", "")
            if title and url:
                results.append(SearchResult(title=title, url=url, snippet=snippet))
        return results
