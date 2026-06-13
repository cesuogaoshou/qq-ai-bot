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


@dataclass(frozen=True)
class StoredMessage:
    id: int
    group_id: int
    user_id: int
    nickname: str
    role: str
    content: str
    created_at: str


@dataclass(frozen=True)
class MessageStats:
    count: int
    oldest_created_at: str | None
    newest_created_at: str | None


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
        await db.execute(
            """
            create table if not exists messages (
                id integer primary key autoincrement,
                group_id integer not null,
                user_id integer not null,
                nickname text not null,
                role text not null,
                content text not null,
                created_at text not null
            )
            """
        )
        await db.execute(
            """
            create table if not exists daily_summaries (
                group_id integer not null,
                summary_date text not null,
                sent_at text not null,
                primary key (group_id, summary_date)
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

    async def add_message(
        self,
        *,
        group_id: int,
        user_id: int,
        nickname: str,
        role: str,
        content: str,
    ) -> StoredMessage:
        db = await self._connect()
        created_at = _now_iso()
        cursor = await db.execute(
            """
            insert into messages (group_id, user_id, nickname, role, content, created_at)
            values (?, ?, ?, ?, ?, ?)
            """,
            (group_id, user_id, nickname, role, content, created_at),
        )
        try:
            message_id = int(cursor.lastrowid)
        finally:
            await cursor.close()
        await db.commit()
        return StoredMessage(
            id=message_id,
            group_id=group_id,
            user_id=user_id,
            nickname=nickname,
            role=role,
            content=content,
            created_at=created_at,
        )

    async def get_recent_messages(self, *, group_id: int, limit: int) -> list[StoredMessage]:
        db = await self._connect()
        cursor = await db.execute(
            """
            select id, group_id, user_id, nickname, role, content, created_at
            from (
                select id, group_id, user_id, nickname, role, content, created_at
                from messages
                where group_id = ?
                order by id desc
                limit ?
            )
            order by id asc
            """,
            (group_id, limit),
        )
        try:
            rows = await cursor.fetchall()
        finally:
            await cursor.close()
        return [_message_from_row(row) for row in rows]

    async def get_messages_between(
        self,
        *,
        group_id: int,
        start_at: str,
        end_at: str,
        limit: int,
    ) -> list[StoredMessage]:
        db = await self._connect()
        cursor = await db.execute(
            """
            select id, group_id, user_id, nickname, role, content, created_at
            from messages
            where group_id = ?
              and created_at >= ?
              and created_at < ?
            order by id asc
            limit ?
            """,
            (group_id, start_at, end_at, limit),
        )
        try:
            rows = await cursor.fetchall()
        finally:
            await cursor.close()
        return [_message_from_row(row) for row in rows]

    async def count_messages(self, *, group_id: int) -> int:
        db = await self._connect()
        cursor = await db.execute(
            "select count(*) from messages where group_id = ?",
            (group_id,),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return int(row[0]) if row is not None else 0

    async def clear_messages(self, *, group_id: int) -> int:
        db = await self._connect()
        cursor = await db.execute(
            "delete from messages where group_id = ?",
            (group_id,),
        )
        try:
            deleted = cursor.rowcount
        finally:
            await cursor.close()
        await db.commit()
        return int(deleted)

    async def get_message_stats(self, *, group_id: int) -> MessageStats:
        db = await self._connect()
        cursor = await db.execute(
            """
            select count(*), min(created_at), max(created_at)
            from messages
            where group_id = ?
            """,
            (group_id,),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        if row is None:
            return MessageStats(count=0, oldest_created_at=None, newest_created_at=None)
        return MessageStats(
            count=int(row[0]),
            oldest_created_at=row[1],
            newest_created_at=row[2],
        )

    async def prune_messages(self, *, group_id: int, keep_latest: int) -> int:
        if keep_latest <= 0:
            return 0
        db = await self._connect()
        cursor = await db.execute(
            """
            delete from messages
            where group_id = ?
              and id not in (
                select id
                from messages
                where group_id = ?
                order by id desc
                limit ?
              )
            """,
            (group_id, group_id, keep_latest),
        )
        try:
            deleted = cursor.rowcount
        finally:
            await cursor.close()
        await db.commit()
        return int(deleted)

    async def has_daily_summary(self, *, group_id: int, summary_date: str) -> bool:
        db = await self._connect()
        cursor = await db.execute(
            """
            select 1
            from daily_summaries
            where group_id = ? and summary_date = ?
            limit 1
            """,
            (group_id, summary_date),
        )
        try:
            row = await cursor.fetchone()
        finally:
            await cursor.close()
        return row is not None

    async def mark_daily_summary_sent(self, *, group_id: int, summary_date: str) -> None:
        db = await self._connect()
        await db.execute(
            """
            insert or replace into daily_summaries (group_id, summary_date, sent_at)
            values (?, ?, ?)
            """,
            (group_id, summary_date, _now_iso()),
        )
        await db.commit()

    async def _connect(self) -> aiosqlite.Connection:
        if self._db is None:
            self._db = await aiosqlite.connect(self.path)
        return self._db


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def _message_from_row(row) -> StoredMessage:
    return StoredMessage(
        id=int(row[0]),
        group_id=int(row[1]),
        user_id=int(row[2]),
        nickname=str(row[3]),
        role=str(row[4]),
        content=str(row[5]),
        created_at=str(row[6]),
    )
