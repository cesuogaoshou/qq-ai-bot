from __future__ import annotations

import httpx


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
