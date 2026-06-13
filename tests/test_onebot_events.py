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


def test_parse_group_message_extracts_image_segments_from_array_message() -> None:
    payload = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 123456,
        "user_id": 42,
        "message": [
            {"type": "at", "data": {"qq": "999"}},
            {"type": "text", "data": {"text": " 看下这张截图"}},
            {
                "type": "image",
                "data": {
                    "file": "abc.image",
                    "url": "http://127.0.0.1:3000/get_image?file=abc.image",
                },
            },
        ],
        "sender": {"nickname": "Alice"},
    }

    event = parse_group_message(payload)

    assert event is not None
    assert event.message == "[CQ:at,qq=999] 看下这张截图"
    assert len(event.image_attachments) == 1
    assert event.image_attachments[0].file == "abc.image"
    assert event.image_attachments[0].url == "http://127.0.0.1:3000/get_image?file=abc.image"


def test_parse_group_message_extracts_image_segments_from_cq_string() -> None:
    payload = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 123456,
        "user_id": 42,
        "message": "[CQ:at,qq=999] 看图 [CQ:image,file=abc.image,url=http://example.com/a.jpg]",
        "sender": {"nickname": "Alice"},
    }

    event = parse_group_message(payload)

    assert event is not None
    assert event.message == "[CQ:at,qq=999] 看图 [CQ:image,file=abc.image,url=http://example.com/a.jpg]"
    assert len(event.image_attachments) == 1
    assert event.image_attachments[0].file == "abc.image"
    assert event.image_attachments[0].url == "http://example.com/a.jpg"


def test_parse_group_message_returns_none_for_non_group_event() -> None:
    payload = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "message": "/bot ping",
    }

    assert parse_group_message(payload) is None
