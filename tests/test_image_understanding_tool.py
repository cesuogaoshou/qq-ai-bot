import pytest
import httpx

from qq_ai_bot.onebot.events import ImageAttachment
from qq_ai_bot.tools.image_understanding import (
    ArkImageUnderstandingClient,
    DisabledImageUnderstandingClient,
    ImageUnderstandingDisabledError,
)


@pytest.mark.anyio
async def test_disabled_image_understanding_client_raises_clear_error() -> None:
    client = DisabledImageUnderstandingClient()

    with pytest.raises(ImageUnderstandingDisabledError, match="Image understanding is disabled"):
        await client.describe(
            prompt="看图",
            images=[ImageAttachment(file="abc.image", url="http://example.com/a.jpg")],
            model="",
        )


@pytest.mark.anyio
async def test_ark_image_understanding_client_posts_openai_compatible_payload() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "图片里有错误日志"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ArkImageUnderstandingClient(
            http=http,
            base_url="https://ark.test/api/v3",
            api_key="secret-key",
        )
        reply = await client.describe(
            prompt="提取图中文字",
            images=[ImageAttachment(file="abc.image", url="http://example.com/a.jpg")],
            model="doubao-vision-test",
        )

    assert reply == "图片里有错误日志"
    assert len(requests) == 1
    assert requests[0].url == "https://ark.test/api/v3/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer secret-key"
    body = requests[0].read()
    assert b'"model":"doubao-vision-test"' in body
    assert b'"type":"text"' in body
    assert '"text":"提取图中文字"'.encode("utf-8") in body
    assert b'"type":"image_url"' in body
    assert b'"url":"http://example.com/a.jpg"' in body


@pytest.mark.anyio
async def test_ark_image_understanding_client_returns_empty_on_http_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = ArkImageUnderstandingClient(
            http=http,
            base_url="https://ark.test/api/v3",
            api_key="secret-key",
        )
        reply = await client.describe(
            prompt="看图",
            images=[ImageAttachment(file="abc.image", url="http://example.com/a.jpg")],
            model="doubao-vision-test",
        )

    assert reply == ""
