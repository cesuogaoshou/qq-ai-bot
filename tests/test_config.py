import pytest

from qq_ai_bot.config import Settings, load_settings


def test_load_settings_reads_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")
    monkeypatch.setenv("BOT_QQ", "3885518851")
    monkeypatch.setenv("LLM_API_KEY", "ark-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    settings = load_settings()

    assert settings == Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        onebot_access_token="token",
        target_group_id=123456,
        bot_qq=3885518851,
        llm_api_key="ark-key",
    )


def test_load_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")
    monkeypatch.setenv("BOT_QQ", "3885518851")
    monkeypatch.setenv("LLM_API_KEY", "ark-key")
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_BASE_URL", raising=False)

    settings = load_settings()

    assert settings.llm_base_url == "https://ark.cn-beijing.volces.com/api/v3"
    assert settings.llm_model == "doubao-seed-2.0-lite"
    assert settings.bot_max_context_messages == 30
    assert settings.bot_max_reply_chars == 300
    assert settings.enable_web_search is False
    assert settings.daily_search_limit_per_group == 20
    assert settings.daily_search_limit_per_user == 5
    assert settings.search_max_results == 3


def test_load_settings_reads_reply_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")
    monkeypatch.setenv("BOT_QQ", "3885518851")
    monkeypatch.setenv("BOT_MAX_REPLY_CHARS", "120")

    settings = load_settings()

    assert settings.bot_max_reply_chars == 120


def test_load_settings_reads_advanced_feature_overrides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")
    monkeypatch.setenv("BOT_QQ", "3885518851")
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "true")
    monkeypatch.setenv("DAILY_SEARCH_LIMIT_PER_GROUP", "7")
    monkeypatch.setenv("DAILY_SEARCH_LIMIT_PER_USER", "2")
    monkeypatch.setenv("SEARCH_MAX_RESULTS", "1")

    settings = load_settings()

    assert settings.enable_web_search is True
    assert settings.daily_search_limit_per_group == 7
    assert settings.daily_search_limit_per_user == 2
    assert settings.search_max_results == 1


def test_load_settings_rejects_missing_target_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("BOT_QQ", "3885518851")
    monkeypatch.setenv("LLM_API_KEY", "ark-key")
    monkeypatch.delenv("TARGET_GROUP_ID", raising=False)

    with pytest.raises(ValueError, match="TARGET_GROUP_ID"):
        load_settings()


def test_load_settings_rejects_missing_bot_qq(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")
    monkeypatch.setenv("LLM_API_KEY", "ark-key")
    monkeypatch.delenv("BOT_QQ", raising=False)

    with pytest.raises(ValueError, match="BOT_QQ"):
        load_settings()


def test_load_settings_allows_missing_llm_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")
    monkeypatch.setenv("BOT_QQ", "3885518851")
    monkeypatch.delenv("LLM_API_KEY", raising=False)

    settings = load_settings()

    assert settings.llm_api_key == ""
