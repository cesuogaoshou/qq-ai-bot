import pytest

from qq_ai_bot.tools.web_search import DisabledWebSearchClient, SearchDisabledError


@pytest.mark.anyio
async def test_disabled_search_client_raises_clear_error() -> None:
    client = DisabledWebSearchClient()

    with pytest.raises(SearchDisabledError, match="Web search is disabled"):
        await client.search("今天有什么新闻", max_results=3)
