from __future__ import annotations

import logging

import httpx

logger = logging.getLogger(__name__)


class LLMClient:
    """OpenAI-compatible chat completion client."""

    def __init__(
        self,
        *,
        http: httpx.AsyncClient,
        base_url: str,
        model: str,
        api_key: str,
        timeout: float = 20.0,
    ) -> None:
        self._http = http
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._api_key = api_key
        self._timeout = timeout

    async def chat(self, messages: list[dict[str, str]]) -> str:
        """Send a chat completion request. Returns reply text or empty string on failure."""
        try:
            response = await self._http.post(
                f"{self._base_url}/chat/completions",
                json={
                    "model": self._model,
                    "messages": messages,
                },
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
            )
            if response.status_code >= 400:
                logger.warning(
                    "LLM chat failed: status=%s body=%s",
                    response.status_code,
                    response.text[:500],
                )
                return ""
            data = response.json()
            choices = data.get("choices", [])
            if not choices:
                logger.warning("LLM chat returned no choices: body=%s", response.text[:500])
                return ""
            content = choices[0].get("message", {}).get("content", "") or ""
            if not content:
                logger.warning("LLM chat returned empty content: body=%s", response.text[:500])
            return content
        except httpx.TimeoutException:
            logger.warning("LLM chat timed out")
            return ""
        except httpx.HTTPError as exc:
            logger.warning("LLM chat failed: error=%s", exc.__class__.__name__)
            return ""
