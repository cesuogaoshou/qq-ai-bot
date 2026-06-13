from qq_ai_bot.policy.image_trigger import detect_image_trigger


def test_detect_image_trigger_requires_explicit_image_wording() -> None:
    trigger = detect_image_trigger("[CQ:at,qq=999] 帮我看下这张截图")

    assert trigger.should_process is True
    assert trigger.prompt == "[CQ:at,qq=999] 帮我看下这张截图"


def test_detect_image_trigger_matches_text_inside_image_wording() -> None:
    trigger = detect_image_trigger("[CQ:at,qq=999] 提取图中文字")

    assert trigger.should_process is True
    assert trigger.prompt == "[CQ:at,qq=999] 提取图中文字"


def test_detect_image_trigger_ignores_plain_chat() -> None:
    trigger = detect_image_trigger("[CQ:at,qq=999] 你好")

    assert trigger.should_process is False
    assert trigger.prompt == ""
