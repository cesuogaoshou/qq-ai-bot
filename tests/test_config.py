import pytest

from qq_ai_bot.config import Settings, load_settings


def test_load_settings_reads_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")

    settings = load_settings()

    assert settings == Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        onebot_access_token="token",
        target_group_id=123456,
    )


def test_load_settings_rejects_missing_target_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.delenv("TARGET_GROUP_ID", raising=False)

    with pytest.raises(ValueError, match="TARGET_GROUP_ID"):
        load_settings()
