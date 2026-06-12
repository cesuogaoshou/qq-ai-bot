from __future__ import annotations

from typing import Protocol

from qq_ai_bot.onebot.events import GroupMessageEvent


class GroupMessageActions(Protocol):
    async def send_group_message(self, group_id: int, message: str) -> None:
        ...


async def handle_group_message(
    event: GroupMessageEvent,
    *,
    target_group_id: int,
    actions: GroupMessageActions,
) -> bool:
    if event.group_id != target_group_id:
        return False
    if event.message.strip() != "/bot ping":
        return False

    await actions.send_group_message(event.group_id, "pong")
    return True
