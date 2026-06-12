from pathlib import Path
from uuid import uuid4

import pytest

from qq_ai_bot.storage.sqlite_store import SQLiteStore


def _sqlite_test_path() -> str:
    directory = Path(".pytest-sqlite")
    directory.mkdir(exist_ok=True)
    return str(directory / f"{uuid4().hex}.sqlite3")


@pytest.mark.anyio
async def test_ensure_group_creates_default_enabled_group() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()

        state = await store.ensure_group(123456)

        assert state.group_id == 123456
        assert state.enabled is True
        assert state.mode == "mention_only"
    finally:
        await store.close()


@pytest.mark.anyio
async def test_set_enabled_persists_group_state() -> None:
    path = _sqlite_test_path()
    store = SQLiteStore(str(path))
    reloaded_store = SQLiteStore(str(path))
    try:
        await store.init()
        await store.ensure_group(123456)

        disabled = await store.set_enabled(123456, False)
        reloaded = await reloaded_store.init_and_get_group(123456)

        assert disabled.enabled is False
        assert reloaded.enabled is False
    finally:
        await store.close()
        await reloaded_store.close()


@pytest.mark.anyio
async def test_messages_persist_in_chronological_order() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()

        await store.add_message(
            group_id=100,
            user_id=1,
            nickname="Alice",
            role="user",
            content="第一条",
        )
        await store.add_message(
            group_id=100,
            user_id=999,
            nickname="bot",
            role="bot",
            content="第二条",
        )

        messages = await store.get_recent_messages(group_id=100, limit=10)

        assert [message.content for message in messages] == ["第一条", "第二条"]
        assert messages[0].nickname == "Alice"
        assert messages[1].role == "bot"
    finally:
        await store.close()


@pytest.mark.anyio
async def test_recent_messages_limit_returns_newest_in_chronological_order() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()

        for index in range(5):
            await store.add_message(
                group_id=100,
                user_id=index,
                nickname=f"User{index}",
                role="user",
                content=f"消息{index}",
            )

        messages = await store.get_recent_messages(group_id=100, limit=3)

        assert [message.content for message in messages] == ["消息2", "消息3", "消息4"]
    finally:
        await store.close()


@pytest.mark.anyio
async def test_clear_messages_removes_target_group_only() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()
        await store.add_message(
            group_id=100,
            user_id=1,
            nickname="Alice",
            role="user",
            content="目标群",
        )
        await store.add_message(
            group_id=200,
            user_id=2,
            nickname="Bob",
            role="user",
            content="其他群",
        )

        deleted = await store.clear_messages(group_id=100)

        assert deleted == 1
        assert await store.count_messages(group_id=100) == 0
        assert await store.count_messages(group_id=200) == 1
    finally:
        await store.close()
