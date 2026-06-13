from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchTrigger:
    should_search: bool
    query: str | None = None
    reason: str | None = None


_EXPLICIT_SEARCH_TERMS = (
    "搜一下",
    "查一下",
    "帮我查",
    "帮我搜",
    "联网查",
    "联网搜索",
    "网上查",
)
_TEMPORAL_TERMS = ("今天", "现在", "最近", "最新", "刚刚", "新闻", "价格", "政策", "版本")


def detect_search_trigger(message: str) -> SearchTrigger:
    query = message.strip()
    if not query:
        return SearchTrigger(should_search=False)
    if _contains_any(query, _EXPLICIT_SEARCH_TERMS):
        return SearchTrigger(should_search=True, query=query, reason="explicit")
    if _contains_any(query, _TEMPORAL_TERMS):
        return SearchTrigger(should_search=True, query=query, reason="temporal")
    return SearchTrigger(should_search=False)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
