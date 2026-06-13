from __future__ import annotations

from typing import Protocol

import httpx

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


class ArkImageUnderstandingClient:
    def __init__(
        self,
        *,
        http: httpx.AsyncClient,
        base_url: str,
        api_key: str,
        timeout: float = 30.0,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    async def describe(
        self,
        *,
        prompt: str,
        images: list[ImageAttachment],
        model: str,
    ) -> str:
        content: list[dict[str, object]] = [{"type": "text", "text": prompt}]
        for image in images:
            if image.url:
                content.append({"type": "image_url", "image_url": {"url": image.url}})

        try:
            response = await self._http.post(
                f"{self._base_url}/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": content}],
                },
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            return choices[0].get("message", {}).get("content", "") or ""
        except httpx.TimeoutException:
            return ""
        except httpx.HTTPError:
            return ""
