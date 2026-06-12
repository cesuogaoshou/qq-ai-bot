from __future__ import annotations

import asyncio
import logging

import httpx
import websockets

from qq_ai_bot.config import load_settings
from qq_ai_bot.onebot.actions import OneBotActionClient
from qq_ai_bot.onebot.client import iter_group_messages
from qq_ai_bot.services.message_loop import handle_group_message


logger = logging.getLogger(__name__)


def build_startup_summary(
    *,
    onebot_ws_url: str,
    onebot_http_url: str,
    access_token: str,
    target_group_id: int,
) -> str:
    token_state = "set" if access_token else "empty"
    return (
        f"onebot_ws_url={onebot_ws_url} "
        f"onebot_http_url={onebot_http_url} "
        f"target_group_id={target_group_id} "
        f"access_token={token_state}"
    )


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    logger.info(
        "Starting QQ AI bot: %s",
        build_startup_summary(
            onebot_ws_url=settings.onebot_ws_url,
            onebot_http_url=settings.onebot_http_url,
            access_token=settings.onebot_access_token,
            target_group_id=settings.target_group_id,
        ),
    )

    async with httpx.AsyncClient(base_url=settings.onebot_http_url, timeout=10) as http:
        actions = OneBotActionClient(
            http=http,
            access_token=settings.onebot_access_token,
        )
        async with websockets.connect(settings.onebot_ws_url) as websocket:
            async for event in iter_group_messages(websocket):
                handled = await handle_group_message(
                    event,
                    target_group_id=settings.target_group_id,
                    actions=actions,
                )
                if handled:
                    logger.info("Handled /bot ping in group %s", event.group_id)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
