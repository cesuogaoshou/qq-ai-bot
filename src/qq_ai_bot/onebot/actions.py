from __future__ import annotations

import httpx


class OneBotActionClient:
    def __init__(self, http: httpx.AsyncClient, access_token: str = "") -> None:
        self._http = http
        self._access_token = access_token

    async def send_group_message(self, group_id: int, message: str) -> None:
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        response = await self._http.post(
            "/send_group_msg",
            json={"group_id": group_id, "message": message},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("retcode") != 0:
            raise RuntimeError(f"OneBot send_group_msg failed: {data}")
