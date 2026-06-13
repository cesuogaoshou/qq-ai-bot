from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime, time, timedelta, timezone, tzinfo
from typing import Protocol

from qq_ai_bot.memory.privacy import redact_sensitive_text
from qq_ai_bot.memory.summary import build_recent_summary_prompt
from qq_ai_bot.storage.sqlite_store import StoredMessage

logger = logging.getLogger(__name__)

DEFAULT_DAILY_SUMMARY_TIMEZONE = timezone(timedelta(hours=8), name="Asia/Shanghai")


class DailySummaryActions(Protocol):
    async def send_group_message(self, group_id: int, message: str) -> None:
        ...


class DailySummaryLLM(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str:
        ...


class DailySummaryStore(Protocol):
    async def get_messages_between(
        self,
        *,
        group_id: int,
        start_at: str,
        end_at: str,
        limit: int,
    ) -> list[StoredMessage]:
        ...

    async def has_daily_summary(self, *, group_id: int, summary_date: str) -> bool:
        ...

    async def mark_daily_summary_sent(self, *, group_id: int, summary_date: str) -> None:
        ...


def build_daily_summary_window(
    *,
    summary_date: date,
    tz: tzinfo = DEFAULT_DAILY_SUMMARY_TIMEZONE,
) -> tuple[str, str]:
    start_local = datetime.combine(summary_date, time.min, tzinfo=tz)
    end_local = start_local + timedelta(days=1)
    return (
        start_local.astimezone(timezone.utc).isoformat(),
        end_local.astimezone(timezone.utc).isoformat(),
    )


def parse_daily_summary_time(value: str) -> time:
    hour_text, minute_text = value.split(":", maxsplit=1)
    return time(hour=int(hour_text), minute=int(minute_text))


def next_daily_summary_run(
    *,
    now: datetime,
    scheduled_time: time,
) -> datetime:
    today_run = datetime.combine(now.date(), scheduled_time, tzinfo=now.tzinfo)
    if now < today_run:
        return today_run
    return today_run + timedelta(days=1)


async def send_daily_summary(
    *,
    group_id: int,
    summary_date: date,
    store: DailySummaryStore,
    actions: DailySummaryActions,
    llm: DailySummaryLLM,
    max_messages: int,
    max_reply_chars: int,
    tz: tzinfo = DEFAULT_DAILY_SUMMARY_TIMEZONE,
) -> bool:
    summary_date_text = summary_date.isoformat()
    if await store.has_daily_summary(group_id=group_id, summary_date=summary_date_text):
        logger.info("Daily summary already sent: group=%s date=%s", group_id, summary_date_text)
        return False

    start_at, end_at = build_daily_summary_window(summary_date=summary_date, tz=tz)
    messages = await store.get_messages_between(
        group_id=group_id,
        start_at=start_at,
        end_at=end_at,
        limit=max_messages,
    )
    if not messages:
        await actions.send_group_message(group_id, "昨日群聊总结：昨天没有可总结的聊天记录。")
        await store.mark_daily_summary_sent(group_id=group_id, summary_date=summary_date_text)
        logger.info("Daily summary empty notice sent: group=%s date=%s", group_id, summary_date_text)
        return True

    prompt = build_recent_summary_prompt(
        [
            {
                "nickname": message.nickname,
                "content": redact_sensitive_text(message.content),
            }
            for message in messages
        ]
    )
    try:
        reply = await llm.chat(prompt)
    except Exception:
        logger.exception("Daily summary LLM call failed: group=%s date=%s", group_id, summary_date_text)
        return False

    if not reply:
        logger.info("Daily summary LLM returned empty reply: group=%s date=%s", group_id, summary_date_text)
        return False

    if len(reply) > max_reply_chars:
        reply = reply[:max_reply_chars]
    await actions.send_group_message(group_id, reply)
    await store.mark_daily_summary_sent(group_id=group_id, summary_date=summary_date_text)
    logger.info(
        "Daily summary sent: group=%s date=%s messages=%d chars=%d",
        group_id,
        summary_date_text,
        len(messages),
        len(reply),
    )
    return True


async def run_daily_summary_scheduler(
    *,
    group_id: int,
    store: DailySummaryStore,
    actions: DailySummaryActions,
    llm: DailySummaryLLM,
    scheduled_time: time,
    lookback_days: int,
    max_messages: int,
    max_reply_chars: int,
    tz: tzinfo = DEFAULT_DAILY_SUMMARY_TIMEZONE,
) -> None:
    while True:
        now = datetime.now(tz=tz)
        today_run = datetime.combine(now.date(), scheduled_time, tzinfo=tz)
        if now >= today_run:
            summary_date = now.date() - timedelta(days=lookback_days)
            await send_daily_summary(
                group_id=group_id,
                summary_date=summary_date,
                store=store,
                actions=actions,
                llm=llm,
                max_messages=max_messages,
                max_reply_chars=max_reply_chars,
                tz=tz,
            )

        next_run = next_daily_summary_run(now=now, scheduled_time=scheduled_time)
        await asyncio.sleep(max(1.0, (next_run - now).total_seconds()))
