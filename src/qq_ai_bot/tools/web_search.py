from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


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
