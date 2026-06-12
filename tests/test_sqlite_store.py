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
