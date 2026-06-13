from __future__ import annotations

import os

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
    daily_search_limit_per_group: int = 20
    daily_search_limit_per_user: int = 5
    search_max_results: int = 3
    bot_admin_qq_ids: set[int] = set()
    bot_group_cooldown_seconds: int = 20
    bot_user_cooldown_seconds: int = 10
    sqlite_path: str = "./data/bot.sqlite3"


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

    return Settings(
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
        daily_search_limit_per_group=int(os.getenv("DAILY_SEARCH_LIMIT_PER_GROUP", "20")),
        daily_search_limit_per_user=int(os.getenv("DAILY_SEARCH_LIMIT_PER_USER", "5")),
        search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "3")),
        bot_admin_qq_ids=_env_int_set("BOT_ADMIN_QQ_IDS"),
        bot_group_cooldown_seconds=int(os.getenv("BOT_GROUP_COOLDOWN_SECONDS", "20")),
        bot_user_cooldown_seconds=int(os.getenv("BOT_USER_COOLDOWN_SECONDS", "10")),
        sqlite_path=os.getenv("SQLITE_PATH", "./data/bot.sqlite3"),
    )
