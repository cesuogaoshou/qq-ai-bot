from types import SimpleNamespace

import httpx
import pytest

from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.config import Settings
from qq_ai_bot.llm.client import LLMClient
from qq_ai_bot.memory.image_cache import RecentImageCache
from qq_ai_bot.main import (
    build_advanced_dependencies,
    build_handler_options,
    build_image_understanding_client,
    build_llm_client,
    build_runtime_dependencies,
    build_startup_summary,
)
from qq_ai_bot.policy.rate_limit import CooldownLimiter
from qq_ai_bot.storage.sqlite_store import SQLiteStore
from qq_ai_bot.tools.image_understanding import (
    ArkImageUnderstandingClient,
    DisabledImageUnderstandingClient,
)
from qq_ai_bot.tools.web_search import DisabledWebSearchClient


def test_build_startup_summary_hides_secrets() -> None:
    summary = build_startup_summary(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        access_token="secret",
        target_group_id=123456,
        bot_qq=999,
        llm_model="test-model",
        llm_api_key="secret-key",
    )

    assert "ws://127.0.0.1:3001" in summary
    assert "http://127.0.0.1:3000" in summary
    assert "123456" in summary
    assert "999" in summary
    assert "test-model" in summary
    assert "access_token=set" in summary
    assert "llm_api_key=set" in summary
    assert "secret" not in summary
    assert "secret-key" not in summary


@pytest.mark.anyio
async def test_build_llm_client_returns_none_without_api_key() -> None:
    settings = SimpleNamespace(
        llm_api_key="",
        llm_base_url="https://test.api",
        llm_model="test-model",
    )

    async with httpx.AsyncClient() as http:
        client = build_llm_client(http=http, settings=settings)

    assert client is None


@pytest.mark.anyio
async def test_build_llm_client_returns_client_with_api_key() -> None:
    settings = SimpleNamespace(
        llm_api_key="secret-key",
        llm_base_url="https://test.api",
        llm_model="test-model",
    )

    async with httpx.AsyncClient() as http:
        client = build_llm_client(http=http, settings=settings)

    assert isinstance(client, LLMClient)


@pytest.mark.anyio
async def test_build_image_understanding_client_returns_disabled_when_feature_off() -> None:
    settings = SimpleNamespace(
        enable_image_input=False,
        image_input_model="doubao-vision-test",
        llm_base_url="https://test.api",
        llm_api_key="secret-key",
    )

    async with httpx.AsyncClient() as http:
        client = build_image_understanding_client(http=http, settings=settings)

    assert isinstance(client, DisabledImageUnderstandingClient)


@pytest.mark.anyio
async def test_build_image_understanding_client_returns_ark_client_when_configured() -> None:
    settings = SimpleNamespace(
        enable_image_input=True,
        image_input_model="doubao-vision-test",
        llm_base_url="https://test.api",
        llm_api_key="secret-key",
        image_max_bytes=1024,
    )

    async with httpx.AsyncClient() as http:
        client = build_image_understanding_client(http=http, settings=settings)

    assert isinstance(client, ArkImageUnderstandingClient)


@pytest.mark.anyio
async def test_build_image_understanding_client_reuses_llm_model_when_image_model_empty() -> None:
    settings = SimpleNamespace(
        enable_image_input=True,
        image_input_model="",
        llm_model="doubao-seed-2.0-lite",
        llm_base_url="https://test.api",
        llm_api_key="secret-key",
        image_max_bytes=1024,
    )

    async with httpx.AsyncClient() as http:
        client = build_image_understanding_client(http=http, settings=settings)

    assert isinstance(client, ArkImageUnderstandingClient)


def test_build_handler_options_uses_reply_limit() -> None:
    settings = SimpleNamespace(
        bot_max_reply_chars=120,
        bot_summary_recent_limit=12,
        bot_memory_max_messages=42,
    )

    assert build_handler_options(settings=settings) == {
        "max_reply_chars": 120,
        "summary_recent_limit": 12,
        "memory_max_messages": 42,
    }


def test_build_advanced_dependencies_uses_settings() -> None:
    settings = Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        target_group_id=100,
        bot_qq=200,
        enable_web_search=True,
        daily_search_limit_per_group=7,
        daily_search_limit_per_user=2,
        search_max_results=1,
        enable_image_input=True,
        daily_image_limit_per_group=3,
        image_input_model="",
        llm_model="doubao-seed-2.0-lite",
        image_max_bytes=1024,
    )

    deps = build_advanced_dependencies(settings)

    assert deps["enable_web_search"] is True
    assert isinstance(deps["search_budget"], DailyUsageBudget)
    assert isinstance(deps["web_search"], DisabledWebSearchClient)
    assert deps["search_max_results"] == 1
    assert deps["enable_image_input"] is True
    assert isinstance(deps["image_budget"], DailyUsageBudget)
    assert isinstance(deps["image_understanding"], DisabledImageUnderstandingClient)
    assert deps["image_input_model"] == "doubao-seed-2.0-lite"
    assert deps["image_max_bytes"] == 1024


def test_build_runtime_dependencies_uses_settings() -> None:
    settings = Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        target_group_id=100,
        bot_qq=200,
        bot_admin_qq_ids={1, 2},
        bot_group_cooldown_seconds=7,
        bot_user_cooldown_seconds=3,
        sqlite_path="./data/test.sqlite3",
    )

    deps = build_runtime_dependencies(settings)

    assert deps["admin_qq_ids"] == {1, 2}
    assert deps["group_cooldown_seconds"] == 7
    assert deps["user_cooldown_seconds"] == 3
    assert isinstance(deps["cooldown_limiter"], CooldownLimiter)
    assert isinstance(deps["group_state_store"], SQLiteStore)


def test_build_runtime_dependencies_includes_image_cache() -> None:
    settings = Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        target_group_id=100,
        bot_qq=200,
    )

    deps = build_runtime_dependencies(settings)

    assert isinstance(deps["image_cache"], RecentImageCache)
