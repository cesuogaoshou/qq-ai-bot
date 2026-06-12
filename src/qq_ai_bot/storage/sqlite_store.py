from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite


@dataclass(frozen=True)
class GroupState:
    group_id: int
    enabled: bool
    mode: str


class SQLiteStore:
    def __init__(self, path: str) -> None:
        self.path = path
        self._db: aiosqlite.Connection | None = None

    async def init(self) -> None:
        db_path = Path(self.path)
        if db_path.parent != Path("."):
            db_path.parent.mkdir(parents=True, exist_ok=True)
        db = await self._connect()
        await db.execute(
            """
            create table if not exists groups (
                group_id integer primary key,
                enabled integer not null,
                mode text not null,
                created_at text not null,
                updated_at text not null
            )
            """
        )
        await db.commit()

    async def close(self) -> None:
        if self._db is not None:
            await self._db.close()
            self._db = None

    async def init_and_get_group(self, group_id: int) -> GroupState:
        await self.init()
        return await self.get_group(group_id)

    async def ensure_group(self, group_id: int) -> GroupState:
        now = _now_iso()
        db = await self._connect()
        await db.execute(
            """
            insert or ignore into groups (group_id, enabled, mode, created_at, updated_at)
            values (?, 1, 'mention_only', ?, ?)
            """,
            (group_id, now, now),
        )
        await db.commit()
        return await self.get_group(group_id)

    async def get_group(self, group_id: int) -> GroupState:
        db = await self._connect()
        cursor = await db.execute(
            "select group_id, enabled, mode from groups where group_id = ?",
            (group_id,),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        if row is None:
            return await self.ensure_group(group_id)
        return GroupState(group_id=int(row[0]), enabled=bool(row[1]), mode=str(row[2]))

    async def set_enabled(self, group_id: int, enabled: bool) -> GroupState:
        await self.ensure_group(group_id)
        db = await self._connect()
        await db.execute(
            """
            update groups
            set enabled = ?, updated_at = ?
            where group_id = ?
            """,
            (1 if enabled else 0, _now_iso(), group_id),
        )
        await db.commit()
        return await self.get_group(group_id)

    async def _connect(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.path)
        return self._db


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()
