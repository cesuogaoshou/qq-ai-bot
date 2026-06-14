from __future__ import annotations

import os
from datetime import time

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Settings(BaseModel):
    onebot_ws_url: str
    onebot_http_url: str
    onebot_access_token: str = ""
    target_group_id: int
    bot_qq: int
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = "doubao-seed-2.0-lite"
    llm_api_key: str = ""
    bot_max_context_messages: int = 30
    bot_summary_recent_limit: int = 100
    bot_memory_max_messages: int = 5000
    bot_max_reply_chars: int = 300
    enable_web_search: bool = False
    web_search_provider: str = "disabled"
    tavily_api_key: str = ""
    web_search_base_url: str = "https://api.tavily.com"
    daily_search_limit_per_group: int = 20
    daily_search_limit_per_user: int = 5
    search_max_results: int = 3
    enable_image_input: bool = False
    daily_image_limit_per_group: int = 5
    daily_image_limit_per_user: int = 5
    image_input_model: str = ""
    image_max_bytes: int = 5_242_880
    bot_admin_qq_ids: set[int] = set()
    bot_group_cooldown_seconds: int = 20
    bot_user_cooldown_seconds: int = 10
    sqlite_path: str = "./data/bot.sqlite3"
    enable_daily_summary: bool = False
    daily_summary_time: str = "09:00"
    daily_summary_lookback_days: int = 1
    daily_summary_max_messages: int = 500


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int_set(name: str) -> set[int]:
    value = os.getenv(name, "")
    if not value.strip():
        return set()
    return {int(part.strip()) for part in value.split(",") if part.strip()}


def load_settings() -> Settings:
    target_group_id = os.getenv("TARGET_GROUP_ID")
    if not target_group_id:
        raise ValueError("TARGET_GROUP_ID is required")

    bot_qq = os.getenv("BOT_QQ")
    if not bot_qq:
        raise ValueError("BOT_QQ is required")

    settings = Settings(
        onebot_ws_url=os.getenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001"),
        onebot_http_url=os.getenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000"),
        onebot_access_token=os.getenv("ONEBOT_ACCESS_TOKEN", ""),
        target_group_id=int(target_group_id),
        bot_qq=int(bot_qq),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"),
        llm_model=os.getenv("LLM_MODEL", "doubao-seed-2.0-lite"),
        llm_api_key=os.getenv("LLM_API_KEY", ""),
        bot_max_context_messages=int(os.getenv("BOT_MAX_CONTEXT_MESSAGES", "30")),
        bot_summary_recent_limit=int(os.getenv("BOT_SUMMARY_RECENT_LIMIT", "100")),
        bot_memory_max_messages=int(os.getenv("BOT_MEMORY_MAX_MESSAGES", "5000")),
        bot_max_reply_chars=int(os.getenv("BOT_MAX_REPLY_CHARS", "300")),
        enable_web_search=_env_bool("ENABLE_WEB_SEARCH", False),
        web_search_provider=os.getenv("WEB_SEARCH_PROVIDER", "disabled"),
        tavily_api_key=os.getenv("TAVILY_API_KEY", ""),
        web_search_base_url=os.getenv("WEB_SEARCH_BASE_URL", "https://api.tavily.com"),
        daily_search_limit_per_group=int(os.getenv("DAILY_SEARCH_LIMIT_PER_GROUP", "20")),
        daily_search_limit_per_user=int(os.getenv("DAILY_SEARCH_LIMIT_PER_USER", "5")),
        search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "3")),
        enable_image_input=_env_bool("ENABLE_IMAGE_INPUT", False),
        daily_image_limit_per_group=int(os.getenv("DAILY_IMAGE_LIMIT_PER_GROUP", "5")),
        daily_image_limit_per_user=int(os.getenv("DAILY_IMAGE_LIMIT_PER_USER", "5")),
        image_input_model=os.getenv("IMAGE_INPUT_MODEL", ""),
        image_max_bytes=int(os.getenv("IMAGE_MAX_BYTES", "5242880")),
        bot_admin_qq_ids=_env_int_set("BOT_ADMIN_QQ_IDS"),
        bot_group_cooldown_seconds=int(os.getenv("BOT_GROUP_COOLDOWN_SECONDS", "20")),
        bot_user_cooldown_seconds=int(os.getenv("BOT_USER_COOLDOWN_SECONDS", "10")),
        sqlite_path=os.getenv("SQLITE_PATH", "./data/bot.sqlite3"),
        enable_daily_summary=_env_bool("ENABLE_DAILY_SUMMARY", False),
        daily_summary_time=os.getenv("DAILY_SUMMARY_TIME", "09:00"),
        daily_summary_lookback_days=int(os.getenv("DAILY_SUMMARY_LOOKBACK_DAYS", "1")),
        daily_summary_max_messages=int(os.getenv("DAILY_SUMMARY_MAX_MESSAGES", "500")),
    )
    _validate_settings(settings)
    return settings


def _validate_settings(settings: Settings) -> None:
    if not settings.llm_model.strip():
        raise ValueError("LLM_MODEL must not be empty")

    if settings.enable_daily_summary:
        _validate_hh_mm("DAILY_SUMMARY_TIME", settings.daily_summary_time)

    if settings.enable_web_search:
        if settings.web_search_provider == "tavily" and not settings.tavily_api_key.strip():
            raise ValueError("TAVILY_API_KEY is required when Tavily web search is enabled")

    if settings.enable_image_input and not settings.llm_api_key.strip():
        raise ValueError("LLM_API_KEY is required when image input is enabled")

    if settings.bot_group_cooldown_seconds < 0:
        raise ValueError("BOT_GROUP_COOLDOWN_SECONDS must be greater than or equal to 0")
    if settings.bot_user_cooldown_seconds < 0:
        raise ValueError("BOT_USER_COOLDOWN_SECONDS must be greater than or equal to 0")


def _validate_hh_mm(name: str, value: str) -> None:
    try:
        hour_text, minute_text = value.split(":", maxsplit=1)
        time(hour=int(hour_text), minute=int(minute_text))
    except (TypeError, ValueError):
        raise ValueError(f"{name} must use HH:MM format") from None
