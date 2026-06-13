from __future__ import annotations

import base64
import logging
from typing import Protocol

import httpx

from qq_ai_bot.onebot.events import ImageAttachment

logger = logging.getLogger(__name__)


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
        max_image_bytes: int = 5_242_880,
        timeout: float = 30.0,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._max_image_bytes = max_image_bytes
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
                image_url = await self._to_model_image_url(image.url)
                content.append({"type": "image_url", "image_url": {"url": image_url}})

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
            if response.status_code >= 400:
                logger.warning(
                    "Ark image understanding failed: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
                return ""
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                return ""
            return choices[0].get("message", {}).get("content", "") or ""
        except httpx.TimeoutException:
            return ""
        except httpx.HTTPError:
            return ""

    async def _to_model_image_url(self, url: str) -> str:
        try:
            response = await self._http.get(url, timeout=self._timeout)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            logger.warning(
                "Image download failed: status=%s url=%s body=%s",
                exc.response.status_code,
                url,
                exc.response.text[:300],
            )
            return url
        except httpx.HTTPError as exc:
            logger.warning(
                "Image download failed: error=%s url=%s",
                exc.__class__.__name__,
                url,
            )
            return url
        content_type = response.headers.get("Content-Type", "image/jpeg").split(";", 1)[0]
        if not content_type.startswith("image/"):
            logger.warning(
                "Image download returned non-image content: content_type=%s url=%s",
                content_type,
                url,
            )
            return url
        image_bytes = response.content
        if len(image_bytes) > self._max_image_bytes:
            logger.warning(
                "Image download exceeded max size: bytes=%d max_bytes=%d url=%s",
                len(image_bytes),
                self._max_image_bytes,
                url,
            )
            return url
        encoded = base64.b64encode(image_bytes).decode("ascii")
        return f"data:{content_type};base64,{encoded}"
