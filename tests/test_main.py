from qq_ai_bot.main import build_startup_summary


def test_build_startup_summary_hides_access_token() -> None:
    summary = build_startup_summary(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        access_token="secret",
        target_group_id=123456,
    )

    assert "ws://127.0.0.1:3001" in summary
    assert "http://127.0.0.1:3000" in summary
    assert "123456" in summary
    assert "secret" not in summary
    assert "access_token=set" in summary
