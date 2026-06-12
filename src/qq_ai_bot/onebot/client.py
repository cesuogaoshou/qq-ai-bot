from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from qq_ai_bot.onebot.events import GroupMessageEvent, parse_group_message


async def iter_group_messages(websocket: Any) -> AsyncIterator[GroupMessageEvent]:
    async for raw_message in websocket:
        payload = json.loads(raw_message)
        event = parse_group_message(payload)
        if event is not None:
            yield event
