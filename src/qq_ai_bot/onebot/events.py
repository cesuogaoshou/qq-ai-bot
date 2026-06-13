from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ImageAttachment(BaseModel):
    file: str = ""
    url: str = ""


class GroupMessageEvent(BaseModel):
    group_id: int
    user_id: int
    message: str
    nickname: str = ""
    message_id: int | None = None
    time: int | None = None
    image_attachments: list[ImageAttachment] = Field(default_factory=list)


def parse_group_message(payload: dict[str, Any]) -> GroupMessageEvent | None:
    if payload.get("post_type") != "message":
        return None
    if payload.get("message_type") != "group":
        return None

    sender = payload.get("sender") or {}
    message, images = _normalize_message(payload.get("message", ""))
    return GroupMessageEvent(
        group_id=int(payload["group_id"]),
        user_id=int(payload["user_id"]),
        message=message,
        nickname=str(sender.get("nickname", "")),
        message_id=payload.get("message_id"),
        time=payload.get("time"),
        image_attachments=images,
    )


def _normalize_message(raw_message: Any) -> tuple[str, list[ImageAttachment]]:
    if isinstance(raw_message, list):
        return _normalize_segment_list(raw_message)
    message = str(raw_message)
    return message, _extract_cq_images(message)


def _normalize_segment_list(segments: list[Any]) -> tuple[str, list[ImageAttachment]]:
    text_parts: list[str] = []
    images: list[ImageAttachment] = []
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        segment_type = str(segment.get("type", ""))
        data = segment.get("data") or {}
        if not isinstance(data, dict):
            data = {}
        if segment_type == "text":
            text_parts.append(str(data.get("text", "")))
        elif segment_type == "at":
            qq = str(data.get("qq", ""))
            if qq:
                text_parts.append(f"[CQ:at,qq={qq}]")
        elif segment_type == "image":
            images.append(
                ImageAttachment(
                    file=str(data.get("file", "")),
                    url=str(data.get("url", "")),
                )
            )
    return "".join(text_parts).strip(), images


def _extract_cq_images(message: str) -> list[ImageAttachment]:
    images: list[ImageAttachment] = []
    start = 0
    marker = "[CQ:image,"
    while True:
        index = message.find(marker, start)
        if index == -1:
            break
        end = message.find("]", index)
        if end == -1:
            break
        params = _parse_cq_params(message[index + len(marker):end])
        images.append(
            ImageAttachment(
                file=params.get("file", ""),
                url=params.get("url", ""),
            )
        )
        start = end + 1
    return images


def _parse_cq_params(params_text: str) -> dict[str, str]:
    params: dict[str, str] = {}
    for part in params_text.split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        params[key] = value
    return params
