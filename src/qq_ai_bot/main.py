from __future__ import annotations

import asyncio
import logging

import httpx
import websockets

from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.config import Settings, load_settings
from qq_ai_bot.llm.client import LLMClient
from qq_ai_bot.memory.image_cache import RecentImageCache
from qq_ai_bot.memory.context import GroupMemory
from qq_ai_bot.onebot.actions import OneBotActionClient
from qq_ai_bot.onebot.client import iter_group_messages
from qq_ai_bot.policy.rate_limit import CooldownLimiter
from qq_ai_bot.services.message_loop import handle_group_message
from qq_ai_bot.storage.sqlite_store import SQLiteStore
from qq_ai_bot.tools.image_understanding import (
    ArkImageUnderstandingClient,
    DisabledImageUnderstandingClient,
)
from qq_ai_bot.tools.web_search import DisabledWebSearchClient


logger = logging.getLogger(__name__)


def build_startup_summary(
    *,
    onebot_ws_url: str,
    onebot_http_url: str,
    access_token: str,
    target_group_id: int,
    bot_qq: int,
    llm_model: str,
    llm_api_key: str,
) -> str:
    token_state = "set" if access_token else "empty"
    llm_state = "set" if llm_api_key else "empty"
    return (
        f"onebot_ws_url={onebot_ws_url} "
        f"onebot_http_url={onebot_http_url} "
        f"target_group_id={target_group_id} "
        f"bot_qq={bot_qq} "
        f"llm_model={llm_model} "
        f"access_token={token_state} "
        f"llm_api_key={llm_state}"
    )


def build_llm_client(*, http: httpx.AsyncClient, settings) -> LLMClient | None:
    if not settings.llm_api_key:
        return None
    return LLMClient(
        http=http,
        base_url=settings.llm_base_url,
        model=settings.llm_model,
        api_key=settings.llm_api_key,
    )


def build_image_understanding_client(
    *,
    http: httpx.AsyncClient,
    settings,
) -> ArkImageUnderstandingClient | DisabledImageUnderstandingClient:
    if not settings.enable_image_input:
        return DisabledImageUnderstandingClient()
    if not settings.image_input_model:
        return DisabledImageUnderstandingClient()
    if not settings.llm_api_key:
        return DisabledImageUnderstandingClient()
    return ArkImageUnderstandingClient(
        http=http,
        base_url=settings.llm_base_url,
        api_key=settings.llm_api_key,
    )


def build_handler_options(*, settings) -> dict[str, int]:
    return {
        "max_reply_chars": settings.bot_max_reply_chars,
        "summary_recent_limit": settings.bot_summary_recent_limit,
        "memory_max_messages": settings.bot_memory_max_messages,
    }


def build_advanced_dependencies(settings: Settings) -> dict[str, object]:
    return {
        "enable_web_search": settings.enable_web_search,
        "search_budget": DailyUsageBudget(
            group_daily_limit=settings.daily_search_limit_per_group,
            user_daily_limit=settings.daily_search_limit_per_user,
        ),
        "web_search": DisabledWebSearchClient(),
        "search_max_results": settings.search_max_results,
        "enable_image_input": settings.enable_image_input,
        "image_budget": DailyUsageBudget(
            group_daily_limit=settings.daily_image_limit_per_group,
            user_daily_limit=settings.daily_image_limit_per_group,
        ),
        "image_understanding": DisabledImageUnderstandingClient(),
        "image_input_model": settings.image_input_model,
        "image_max_bytes": settings.image_max_bytes,
    }


def build_runtime_dependencies(settings: Settings) -> dict[str, object]:
    return {
        "admin_qq_ids": settings.bot_admin_qq_ids,
        "group_state_store": SQLiteStore(settings.sqlite_path),
        "image_cache": RecentImageCache(),
        "cooldown_limiter": CooldownLimiter(
            group_cooldown_seconds=settings.bot_group_cooldown_seconds,
            user_cooldown_seconds=settings.bot_user_cooldown_seconds,
        ),
        "group_cooldown_seconds": settings.bot_group_cooldown_seconds,
        "user_cooldown_seconds": settings.bot_user_cooldown_seconds,
    }


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
            bot_qq=settings.bot_qq,
            llm_model=settings.llm_model,
            llm_api_key=settings.llm_api_key,
        ),
    )

    memory = GroupMemory(max_messages=settings.bot_max_context_messages)
    advanced_dependencies = build_advanced_dependencies(settings)
    runtime_dependencies = build_runtime_dependencies(settings)
    group_state_store = runtime_dependencies["group_state_store"]
    if isinstance(group_state_store, SQLiteStore):
        await group_state_store.init()
        await group_state_store.ensure_group(settings.target_group_id)

    try:
        async with (
            httpx.AsyncClient(base_url=settings.onebot_http_url, timeout=10) as onebot_http,
            httpx.AsyncClient(timeout=30) as llm_http,
        ):
            actions = OneBotActionClient(
                http=onebot_http,
                access_token=settings.onebot_access_token,
            )
            llm = build_llm_client(http=llm_http, settings=settings)
            advanced_dependencies["image_understanding"] = build_image_understanding_client(
                http=llm_http,
                settings=settings,
            )

            ws_url = settings.onebot_ws_url
            if settings.onebot_access_token:
                ws_url = f"{settings.onebot_ws_url}?access_token={settings.onebot_access_token}"
            async with websockets.connect(ws_url) as websocket:
                async for event in iter_group_messages(websocket):
                    handled = await handle_group_message(
                        event,
                        target_group_id=settings.target_group_id,
                        bot_qq=settings.bot_qq,
                        actions=actions,
                        llm=llm,
                        memory=memory,
                        **build_handler_options(settings=settings),
                        **advanced_dependencies,
                        **runtime_dependencies,
                    )
                    if handled:
                        logger.info("Handled message in group %s", event.group_id)
    finally:
        if isinstance(group_state_store, SQLiteStore):
            await group_state_store.close()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
