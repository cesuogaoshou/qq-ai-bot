from qq_ai_bot.onebot.events import GroupMessageEvent, parse_group_message


def test_parse_group_message_from_onebot_payload() -> None:
    payload = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 123456,
        "user_id": 42,
        "message": "/bot ping",
        "sender": {"nickname": "Alice"},
        "message_id": 1001,
        "time": 1710000000,
    }

    event = parse_group_message(payload)

    assert event == GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="/bot ping",
        nickname="Alice",
        message_id=1001,
        time=1710000000,
    )


def test_parse_group_message_returns_none_for_non_group_event() -> None:
    payload = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "message": "/bot ping",
    }

    assert parse_group_message(payload) is None
