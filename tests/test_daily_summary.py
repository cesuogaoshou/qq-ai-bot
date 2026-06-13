from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from qq_ai_bot.services.daily_summary import (
    build_daily_summary_window,
    send_daily_summary,
)
from qq_ai_bot.storage.sqlite_store import StoredMessage


class FakeActions:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_group_message(self, group_id: int, message: str) -> None:
        self.sent.append((group_id, message))


class FakeLLM:
    def __init__(self, reply: str = "summary reply") -> None:
        self.reply = reply
        self.messages: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.messages.append(messages)
        return self.reply


class FakeStore:
    def __init__(self, messages: list[StoredMessage] | None = None) -> None:
        self.messages = messages or []
        self.sent_dates: set[tuple[int, str]] = set()
        self.queries: list[tuple[int, str, str, int]] = []

    async def get_messages_between(
        self,
        *,
        group_id: int,
        start_at: str,
        end_at: str,
        limit: int,
    ) -> list[StoredMessage]:
        self.queries.append((group_id, start_at, end_at, limit))
        return self.messages[:limit]

    async def has_daily_summary(self, *, group_id: int, summary_date: str) -> bool:
        return (group_id, summary_date) in self.sent_dates

    async def mark_daily_summary_sent(self, *, group_id: int, summary_date: str) -> None:
        self.sent_dates.add((group_id, summary_date))


def _message(content: str) -> StoredMessage:
    return StoredMessage(
        id=1,
        group_id=100,
        user_id=1,
        nickname="Alice",
        role="user",
        content=content,
        created_at="2026-06-13T01:00:00+00:00",
    )


def test_build_daily_summary_window_uses_asia_shanghai_day_boundaries() -> None:
    start_at, end_at = build_daily_summary_window(
        summary_date=date(2026, 6, 13),
        tz=timezone(timedelta(hours=8)),
    )

    assert start_at == "2026-06-12T16:00:00+00:00"
    assert end_at == "2026-06-13T16:00:00+00:00"


@pytest.mark.anyio
async def test_send_daily_summary_summarizes_yesterday_messages() -> None:
    store = FakeStore(messages=[_message("phone 13800138000"), _message("normal chat")])
    actions = FakeActions()
    llm = FakeLLM(reply="Yesterday summary")

    sent = await send_daily_summary(
        group_id=100,
        summary_date=date(2026, 6, 13),
        store=store,
        actions=actions,
        llm=llm,
        max_messages=500,
        max_reply_chars=300,
    )

    assert sent is True
    assert actions.sent == [(100, "Yesterday summary")]
    assert store.sent_dates == {(100, "2026-06-13")}
    assert store.queries == [
        (100, "2026-06-12T16:00:00+00:00", "2026-06-13T16:00:00+00:00", 500)
    ]
    assert "13800138000" not in llm.messages[0][1]["content"]


@pytest.mark.anyio
async def test_send_daily_summary_sends_empty_notice_without_llm_call() -> None:
    store = FakeStore(messages=[])
    actions = FakeActions()
    llm = FakeLLM()

    sent = await send_daily_summary(
        group_id=100,
        summary_date=date(2026, 6, 13),
        store=store,
        actions=actions,
        llm=llm,
        max_messages=500,
        max_reply_chars=300,
    )

    assert sent is True
    assert actions.sent == [(100, "昨日群聊总结：昨天没有可总结的聊天记录。")]
    assert llm.messages == []
    assert store.sent_dates == {(100, "2026-06-13")}


@pytest.mark.anyio
async def test_send_daily_summary_skips_already_sent_date() -> None:
    store = FakeStore(messages=[_message("normal chat")])
    store.sent_dates.add((100, "2026-06-13"))
    actions = FakeActions()
    llm = FakeLLM()

    sent = await send_daily_summary(
        group_id=100,
        summary_date=date(2026, 6, 13),
        store=store,
        actions=actions,
        llm=llm,
        max_messages=500,
        max_reply_chars=300,
    )

    assert sent is False
    assert actions.sent == []
    assert llm.messages == []
    assert store.queries == []


@pytest.mark.anyio
async def test_send_daily_summary_truncates_llm_reply() -> None:
    store = FakeStore(messages=[_message("normal chat")])
    actions = FakeActions()
    llm = FakeLLM(reply="abcdef")

    sent = await send_daily_summary(
        group_id=100,
        summary_date=date(2026, 6, 13),
        store=store,
        actions=actions,
        llm=llm,
        max_messages=500,
        max_reply_chars=3,
    )

    assert sent is True
    assert actions.sent == [(100, "abc")]
