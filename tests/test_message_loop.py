import pytest

from qq_ai_bot.memory.context import GroupMemory
from qq_ai_bot.onebot.events import GroupMessageEvent
from qq_ai_bot.services.message_loop import handle_group_message


class FakeActions:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_group_message(self, group_id: int, message: str) -> None:
        self.sent.append((group_id, message))


@pytest.mark.anyio
async def test_replies_to_ping_in_target_group() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456, user_id=42, message=" /bot ping ", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions,
    )

    assert handled is True
    assert actions.sent == [(123456, "pong")]


@pytest.mark.anyio
async def test_ignores_other_groups() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=999999, user_id=42, message="/bot ping", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions,
    )

    assert handled is False
    assert actions.sent == []


@pytest.mark.anyio
async def test_at_bot_triggers_llm_reply() -> None:
    actions = FakeActions()

    class FakeLLM:
        async def chat(self, messages: list[dict[str, str]]) -> str:
            return "这是 LLM 的回复"

    memory = GroupMemory(max_messages=30)
    llm = FakeLLM()
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=999] 你好啊", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
    )

    assert handled is True
    assert len(actions.sent) == 1
    assert actions.sent[0] == (123456, "这是 LLM 的回复")
    assert memory.get_recent() == [
        {"role": "user", "content": "Alice: [CQ:at,qq=999] 你好啊"},
        {"role": "user", "content": "bot: 这是 LLM 的回复"},
    ]


@pytest.mark.anyio
async def test_at_bot_llm_empty_reply_no_send() -> None:
    actions = FakeActions()

    class FakeLLM:
        async def chat(self, messages: list[dict[str, str]]) -> str:
            return ""

    memory = GroupMemory(max_messages=30)
    llm = FakeLLM()
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=999] 你好", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
    )

    assert handled is True
    assert actions.sent == []


@pytest.mark.anyio
async def test_no_at_no_ping_ignored() -> None:
    actions = FakeActions()
    memory = GroupMemory(max_messages=30)
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="普通聊天消息", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions, memory=memory,
    )

    assert handled is False
    assert actions.sent == []
    assert memory.get_recent() == [
        {"role": "user", "content": "Alice: 普通聊天消息"}
    ]


@pytest.mark.anyio
async def test_at_other_qq_ignored() -> None:
    actions = FakeActions()
    memory = GroupMemory(max_messages=30)

    class FakeLLM:
        async def chat(self, messages: list[dict[str, str]]) -> str:
            return "不应该被调用"

    llm = FakeLLM()
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=123456] 叫你", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
    )

    assert handled is False
    assert actions.sent == []


@pytest.mark.anyio
async def test_reply_truncated_to_max_chars() -> None:
    actions = FakeActions()
    long_reply = "A" * 500

    class FakeLLM:
        async def chat(self, messages: list[dict[str, str]]) -> str:
            return long_reply

    memory = GroupMemory(max_messages=30)
    llm = FakeLLM()
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=999] 你好", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
        max_reply_chars=300,
    )

    assert handled is True
    assert len(actions.sent) == 1
    assert len(actions.sent[0][1]) == 300


@pytest.mark.anyio
async def test_ping_takes_priority_over_at() -> None:
    """If message contains both /bot ping and an @, ping wins."""
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="/bot ping [CQ:at,qq=999]", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions,
    )

    assert handled is True
    assert actions.sent == [(123456, "pong")]
