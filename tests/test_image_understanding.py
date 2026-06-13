import logging

import httpx
import pytest

from qq_ai_bot.onebot.events import ImageAttachment
from qq_ai_bot.tools.image_understanding import ArkImageUnderstandingClient


@pytest.mark.anyio
async def test_ark_image_client_logs_image_download_failure(caplog) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(404, text="expired", request=request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "图片描述"}}]},
            request=request,
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
        client = ArkImageUnderstandingClient(
            http=http,
            base_url="https://ark.example.test/api/v3",
            api_key="test-key",
        )

        with caplog.at_level(logging.WARNING, logger="qq_ai_bot.tools.image_understanding"):
            reply = await client.describe(
                prompt="看图",
                images=[ImageAttachment(file="a.jpg", url="https://qq.example.test/a.jpg")],
                model="doubao-seed-2.0-lite",
            )

    assert reply == "图片描述"
    assert "Image download failed" in caplog.text
    assert "status=404" in caplog.text
