from __future__ import annotations

from typing import Protocol

from qq_ai_bot.onebot.events import ImageAttachment


class ImageUnderstandingDisabledError(RuntimeError):
    pass


class ImageUnderstandingClient(Protocol):
    async def describe(
        self,
        *,
        prompt: str,
        images: list[ImageAttachment],
        model: str,
    ) -> str:
        ...


class DisabledImageUnderstandingClient:
    async def describe(
        self,
        *,
        prompt: str,
        images: list[ImageAttachment],
        model: str,
    ) -> str:
        raise ImageUnderstandingDisabledError("Image understanding is disabled")
