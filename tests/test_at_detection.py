from qq_ai_bot.onebot.utils import is_at_bot, parse_at_qqs


def test_parse_single_at() -> None:
    qqs = parse_at_qqs("[CQ:at,qq=3885518851] 你好")
    assert qqs == [3885518851]


def test_parse_multiple_at() -> None:
    qqs = parse_at_qqs("[CQ:at,qq=3885518851] [CQ:at,qq=123456] 一起出来")
    assert qqs == [3885518851, 123456]


def test_parse_no_at() -> None:
    qqs = parse_at_qqs("大家好今天吃什么")
    assert qqs == []


def test_parse_at_in_middle_of_text() -> None:
    qqs = parse_at_qqs("来看看 [CQ:at,qq=3885518851] 这个问题")
    assert qqs == [3885518851]


def test_parse_empty_string() -> None:
    qqs = parse_at_qqs("")
    assert qqs == []


def test_parse_at_with_name_param() -> None:
    qqs = parse_at_qqs("[CQ:at,qq=3885518851,name=厕所高手] 在吗")
    assert qqs == [3885518851]


def test_is_at_bot_true() -> None:
    assert is_at_bot("[CQ:at,qq=3885518851] 你好", bot_qq=3885518851) is True


def test_is_at_bot_false_other_qq() -> None:
    assert is_at_bot("[CQ:at,qq=123456] 你好", bot_qq=3885518851) is False


def test_is_at_bot_false_no_at() -> None:
    assert is_at_bot("你好", bot_qq=3885518851) is False


def test_is_at_bot_multiple_at_one_matches() -> None:
    assert is_at_bot("[CQ:at,qq=123456] [CQ:at,qq=3885518851] 看看", bot_qq=3885518851) is True
