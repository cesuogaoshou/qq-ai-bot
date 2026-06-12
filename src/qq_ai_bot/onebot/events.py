from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class GroupMessageEvent(BaseModel):
    group_id: int
    user_id: int
    message: str
    nickname: str = ""
    message_id: int | None = None
    time: int | None = None


def parse_group_message(payload: dict[str, Any]) -> GroupMessageEvent | None:
    if payload.get("post_type") != "message":
        return None
    if payload.get("message_type") != "group":
        return None

    sender = payload.get("sender") or {}
    return GroupMessageEvent(
        group_id=int(payload["group_id"]),
        user_id=int(payload["user_id"]),
        message=str(payload.get("message", "")),
        nickname=str(sender.get("nickname", "")),
        message_id=payload.get("message_id"),
        time=payload.get("time"),
    )
