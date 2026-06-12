import pytest

from qq_ai_bot.onebot.events import GroupMessageEvent
from qq_ai_bot.services.message_loop import handle_group_message


class FakeActions:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_group_message(self, group_id: int, message: str) -> None:
        self.sent.append((group_id, message))


@pytest.mark.anyio
async def test_handle_group_message_replies_to_ping_in_target_group() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message=" /bot ping ",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        actions=actions,
    )

    assert handled is True
    assert actions.sent == [(123456, "pong")]


@pytest.mark.anyio
async def test_handle_group_message_ignores_other_groups() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=999999,
        user_id=42,
        message="/bot ping",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        actions=actions,
    )

    assert handled is False
    assert actions.sent == []


@pytest.mark.anyio
async def test_handle_group_message_ignores_non_ping_messages() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="hello",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        actions=actions,
    )

    assert handled is False
    assert actions.sent == []
