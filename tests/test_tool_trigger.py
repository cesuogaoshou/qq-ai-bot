from qq_ai_bot.policy.tool_trigger import SearchTrigger, detect_search_trigger


def test_explicit_search_request_triggers_search() -> None:
    trigger = detect_search_trigger("帮我搜一下今天豆包模型有什么更新")

    assert trigger.should_search is True
    assert trigger.reason == "explicit"


def test_temporal_question_triggers_search() -> None:
    trigger = detect_search_trigger("现在 Python 最新版本是多少")

    assert trigger.should_search is True
    assert trigger.reason == "temporal"


def test_normal_question_does_not_trigger_search() -> None:
    trigger = detect_search_trigger("Python list 和 tuple 有什么区别")

    assert trigger == SearchTrigger(should_search=False, query=None, reason=None)


def test_empty_message_does_not_trigger_search() -> None:
    trigger = detect_search_trigger("   ")

    assert trigger.should_search is False
    assert trigger.query is None
