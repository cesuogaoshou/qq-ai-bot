import httpx
import pytest

from qq_ai_bot.onebot.actions import OneBotActionClient


@pytest.mark.anyio
async def test_send_group_message_posts_onebot_action() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "ok", "retcode": 0, "data": {}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://onebot.test") as http:
        client = OneBotActionClient(http=http, access_token="secret")
        await client.send_group_message(group_id=123456, message="pong")

    assert len(requests) == 1
    assert requests[0].url.path == "/send_group_msg"
    assert requests[0].headers["Authorization"] == "Bearer secret"
    assert requests[0].read() == b'{"group_id":123456,"message":"pong"}'
