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


@pytest.mark.anyio
async def test_message_stats_include_count_oldest_and_newest() -> None:
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
            user_id=2,
            nickname="Bob",
            role="user",
            content="第二条",
        )

        stats = await store.get_message_stats(group_id=100)

        assert stats.count == 2
        assert stats.oldest_created_at is not None
        assert stats.newest_created_at is not None
        assert stats.oldest_created_at <= stats.newest_created_at
    finally:
        await store.close()


@pytest.mark.anyio
async def test_message_stats_empty_group() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()

        stats = await store.get_message_stats(group_id=100)

        assert stats.count == 0
        assert stats.oldest_created_at is None
        assert stats.newest_created_at is None
    finally:
        await store.close()


@pytest.mark.anyio
async def test_prune_messages_keeps_latest_for_target_group_only() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()
        for index in range(5):
            await store.add_message(
                group_id=100,
                user_id=index,
                nickname=f"User{index}",
                role="user",
                content=f"目标{index}",
            )
        await store.add_message(
            group_id=200,
            user_id=1,
            nickname="Other",
            role="user",
            content="其他群",
        )

        deleted = await store.prune_messages(group_id=100, keep_latest=2)

        assert deleted == 3
        assert [message.content for message in await store.get_recent_messages(group_id=100, limit=10)] == [
            "目标3",
            "目标4",
        ]
        assert await store.count_messages(group_id=200) == 1
    finally:
        await store.close()


@pytest.mark.anyio
async def test_prune_messages_ignores_non_positive_limit() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()
        await store.add_message(
            group_id=100,
            user_id=1,
            nickname="Alice",
            role="user",
            content="保留",
        )

        deleted = await store.prune_messages(group_id=100, keep_latest=0)

        assert deleted == 0
        assert await store.count_messages(group_id=100) == 1
    finally:
        await store.close()


@pytest.mark.anyio
async def test_get_messages_between_returns_target_group_messages_in_range() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()
        db = await store._connect()
        await db.executemany(
            """
            insert into messages (group_id, user_id, nickname, role, content, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            [
                (100, 1, "Alice", "user", "before", "2026-06-12T15:59:59+00:00"),
                (100, 1, "Alice", "user", "first", "2026-06-12T16:00:00+00:00"),
                (200, 2, "Bob", "user", "other group", "2026-06-12T17:00:00+00:00"),
                (100, 3, "Carol", "user", "second", "2026-06-13T15:59:59+00:00"),
                (100, 4, "Dave", "user", "after", "2026-06-13T16:00:00+00:00"),
            ],
        )
        await db.commit()

        messages = await store.get_messages_between(
            group_id=100,
            start_at="2026-06-12T16:00:00+00:00",
            end_at="2026-06-13T16:00:00+00:00",
            limit=10,
        )

        assert [message.content for message in messages] == ["first", "second"]
    finally:
        await store.close()


@pytest.mark.anyio
async def test_get_messages_between_respects_limit() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()
        for index in range(3):
            await store.add_message(
                group_id=100,
                user_id=index,
                nickname=f"User{index}",
                role="user",
                content=f"message-{index}",
            )

        messages = await store.get_messages_between(
            group_id=100,
            start_at="2000-01-01T00:00:00+00:00",
            end_at="2999-01-01T00:00:00+00:00",
            limit=2,
        )

        assert [message.content for message in messages] == ["message-0", "message-1"]
    finally:
        await store.close()


@pytest.mark.anyio
async def test_daily_summary_marker_prevents_duplicate_pushes() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()

        assert await store.has_daily_summary(group_id=100, summary_date="2026-06-13") is False

        await store.mark_daily_summary_sent(group_id=100, summary_date="2026-06-13")
        await store.mark_daily_summary_sent(group_id=100, summary_date="2026-06-13")

        assert await store.has_daily_summary(group_id=100, summary_date="2026-06-13") is True
    finally:
        await store.close()


@pytest.mark.anyio
async def test_init_creates_messages_group_created_at_index() -> None:
    store = SQLiteStore(_sqlite_test_path())
    try:
        await store.init()
        db = await store._connect()
        cursor = await db.execute("pragma index_list(messages)")
        try:
            rows = await cursor.fetchall()
        finally:
            await cursor.close()

        assert any(row[1] == "idx_messages_group_created_at" for row in rows)
    finally:
        await store.close()
