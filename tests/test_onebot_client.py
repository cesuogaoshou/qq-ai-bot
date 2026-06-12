import json

import pytest

from qq_ai_bot.onebot.client import iter_group_messages


class FakeWebSocket:
    def __init__(self, payloads: list[dict]) -> None:
        self._messages = [json.dumps(payload) for payload in payloads]

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


@pytest.mark.anyio
async def test_iter_group_messages_yields_only_group_messages() -> None:
    websocket = FakeWebSocket(
        [
            {
                "post_type": "message",
                "message_type": "private",
                "user_id": 1,
                "message": "ignored",
            },
            {
                "post_type": "message",
                "message_type": "group",
                "group_id": 123456,
                "user_id": 42,
                "message": "/bot ping",
                "sender": {"nickname": "Alice"},
            },
        ]
    )

    events = [event async for event in iter_group_messages(websocket)]

    assert len(events) == 1
    assert events[0].group_id == 123456
    assert events[0].message == "/bot ping"
