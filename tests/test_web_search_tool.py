import pytest
import httpx

from qq_ai_bot.tools.web_search import (
    DisabledWebSearchClient,
    SearchDisabledError,
    TavilySearchClient,
)


@pytest.mark.anyio
async def test_disabled_search_client_raises_clear_error() -> None:
    client = DisabledWebSearchClient()

    with pytest.raises(SearchDisabledError, match="Web search is disabled"):
        await client.search("今天有什么新闻", max_results=3)


@pytest.mark.anyio
async def test_tavily_search_client_posts_query_and_maps_results() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={
                "results": [
                    {
                        "title": "模型更新",
                        "url": "https://example.com/model",
                        "content": "今天发布了新的模型能力说明。",
                    }
                ]
            },
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = TavilySearchClient(
            http=http,
            base_url="https://api.tavily.com",
            api_key="test-key",
        )

        results = await client.search("今天豆包有什么更新", max_results=2)

    assert len(results) == 1
    assert results[0].title == "模型更新"
    assert results[0].url == "https://example.com/model"
    assert results[0].snippet == "今天发布了新的模型能力说明。"
    assert requests[0].url == "https://api.tavily.com/search"
    assert requests[0].headers["Authorization"] == "Bearer test-key"
    assert requests[0].read()
    assert '"query":"今天豆包有什么更新"'.encode() in requests[0].content
    assert b'"max_results":2' in requests[0].content


@pytest.mark.anyio
async def test_tavily_search_client_returns_empty_results_on_provider_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text="provider error", request=request)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = TavilySearchClient(
            http=http,
            base_url="https://api.tavily.com",
            api_key="test-key",
        )

        results = await client.search("今天豆包有什么更新", max_results=2)

    assert results == []
