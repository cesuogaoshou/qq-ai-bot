from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from typing import Protocol

from qq_ai_bot.admin.auth import is_admin
from qq_ai_bot.admin.commands import AdminCommandType, parse_admin_command
from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.llm.prompt import build_prompt
from qq_ai_bot.memory.context import GroupMemory
from qq_ai_bot.memory.privacy import redact_sensitive_text
from qq_ai_bot.memory.summary import build_recent_summary_prompt
from qq_ai_bot.onebot.events import GroupMessageEvent
from qq_ai_bot.onebot.events import ImageAttachment
from qq_ai_bot.policy.image_trigger import detect_image_trigger
from qq_ai_bot.onebot.utils import is_at_bot
from qq_ai_bot.policy.rate_limit import CooldownLimiter
from qq_ai_bot.policy.safety import SafetyAction, classify_message_safety
from qq_ai_bot.policy.tool_trigger import detect_search_trigger
from qq_ai_bot.storage.sqlite_store import GroupState
from qq_ai_bot.tools.image_understanding import (
    ImageUnderstandingClient,
    ImageUnderstandingDisabledError,
)
from qq_ai_bot.tools.web_search import SearchDisabledError, WebSearchClient

logger = logging.getLogger(__name__)


class GroupMessageActions(Protocol):
    async def send_group_message(self, group_id: int, message: str) -> None:
        ...


class LLMChat(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str:
        ...


class ImageUnderstanding(Protocol):
    async def describe(
        self,
        *,
        prompt: str,
        images: list[ImageAttachment],
        model: str,
    ) -> str:
        ...


class GroupStateStore(Protocol):
    async def get_group(self, group_id: int) -> GroupState:
        ...

    async def set_enabled(self, group_id: int, enabled: bool) -> GroupState:
        ...

    async def add_message(
        self,
        *,
        group_id: int,
        user_id: int,
        nickname: str,
        role: str,
        content: str,
    ):
        ...

    async def get_recent_messages(self, *, group_id: int, limit: int):
        ...

    async def count_messages(self, *, group_id: int) -> int:
        ...

    async def clear_messages(self, *, group_id: int) -> int:
        ...

    async def get_message_stats(self, *, group_id: int):
        ...

    async def prune_messages(self, *, group_id: int, keep_latest: int) -> int:
        ...


async def handle_group_message(
    event: GroupMessageEvent,
    *,
    target_group_id: int,
    bot_qq: int,
    actions: GroupMessageActions,
    llm: LLMChat | None = None,
    memory: GroupMemory | None = None,
    max_reply_chars: int = 300,
    enable_web_search: bool = False,
    search_budget: DailyUsageBudget | None = None,
    web_search: WebSearchClient | None = None,
    search_max_results: int = 3,
    enable_image_input: bool = False,
    image_budget: DailyUsageBudget | None = None,
    image_understanding: ImageUnderstandingClient | ImageUnderstanding | None = None,
    image_input_model: str = "",
    image_max_bytes: int = 5_242_880,
    group_state_store: GroupStateStore | None = None,
    admin_qq_ids: set[int] | None = None,
    cooldown_limiter: CooldownLimiter | None = None,
    group_cooldown_seconds: int = 20,
    user_cooldown_seconds: int = 10,
    summary_recent_limit: int = 100,
    memory_max_messages: int = 5000,
) -> bool:
    if event.group_id != target_group_id:
        return False

    message_text = event.message.strip()

    # /bot ping — fixed reply, no LLM needed
    if message_text.startswith("/bot ping"):
        await actions.send_group_message(event.group_id, "pong")
        return True

    admin_command = parse_admin_command(message_text)
    if admin_command is not None:
        if not is_admin(user_id=event.user_id, admin_ids=admin_qq_ids or set()):
            await actions.send_group_message(event.group_id, "你没有权限执行这个命令。")
            return True
        if group_state_store is None:
            await actions.send_group_message(event.group_id, "运行状态存储未启用。")
            return True
        if admin_command.type == AdminCommandType.ON:
            await group_state_store.set_enabled(event.group_id, True)
            await actions.send_group_message(event.group_id, "机器人已开启。")
            return True
        if admin_command.type == AdminCommandType.OFF:
            await group_state_store.set_enabled(event.group_id, False)
            await actions.send_group_message(event.group_id, "机器人已关闭。")
            return True
        if admin_command.type == AdminCommandType.STATUS:
            group_state = await group_state_store.get_group(event.group_id)
            await actions.send_group_message(
                event.group_id,
                (
                    f"enabled={group_state.enabled} "
                    f"mode={group_state.mode} "
                    f"web_search={enable_web_search} "
                    f"image_input={enable_image_input} "
                    f"group_cooldown={group_cooldown_seconds}s "
                    f"user_cooldown={user_cooldown_seconds}s"
                ),
            )
            return True
        if admin_command.type == AdminCommandType.SUMMARY_RECENT:
            if llm is None:
                await actions.send_group_message(
                    event.group_id,
                    "当前未配置大模型，无法生成聊天总结。",
                )
                return True
            recent_messages = await group_state_store.get_recent_messages(
                group_id=event.group_id,
                limit=summary_recent_limit,
            )
            if not recent_messages:
                await actions.send_group_message(event.group_id, "没有可总结的最近聊天记录。")
                return True
            summary_prompt = build_recent_summary_prompt(
                [
                    {
                        "nickname": message.nickname,
                        "content": redact_sensitive_text(message.content),
                    }
                    for message in recent_messages
                ]
            )
            try:
                reply = await llm.chat(summary_prompt)
            except Exception:
                logger.exception("Summary LLM call failed for group %s", event.group_id)
                return False
            if reply:
                if len(reply) > max_reply_chars:
                    reply = reply[:max_reply_chars]
                await actions.send_group_message(event.group_id, reply)
            return True
        if admin_command.type == AdminCommandType.MEMORY_STATUS:
            stats = await group_state_store.get_message_stats(group_id=event.group_id)
            await actions.send_group_message(
                event.group_id,
                (
                    f"messages={stats.count} "
                    f"oldest={stats.oldest_created_at or 'none'} "
                    f"newest={stats.newest_created_at or 'none'} "
                    f"summary=not_persisted"
                ),
            )
            return True
        if admin_command.type == AdminCommandType.MEMORY_CLEAR:
            deleted = await group_state_store.clear_messages(group_id=event.group_id)
            await actions.send_group_message(event.group_id, f"已清理 {deleted} 条聊天记忆。")
            return True
        if admin_command.type == AdminCommandType.SUMMARY_CLEAR:
            await actions.send_group_message(event.group_id, "当前没有持久化摘要可清理。")
            return True
        await actions.send_group_message(event.group_id, "未知命令。")
        return True

    at_bot = is_at_bot(event.message, bot_qq=bot_qq)
    if group_state_store is not None:
        group_state = await group_state_store.get_group(event.group_id)
        if not group_state.enabled:
            return True

    safety = classify_message_safety(message_text)
    if safety.action in {SafetyAction.DEESCALATE, SafetyAction.REFUSE} and at_bot:
        if safety.reply:
            await actions.send_group_message(event.group_id, safety.reply)
        return True

    image_trigger = detect_image_trigger(message_text)
    if at_bot and image_trigger.should_process:
        if not enable_image_input:
            await actions.send_group_message(
                event.group_id,
                "图片理解当前未开启。你可以让管理员确认模型能力和费用后再开启。",
            )
            return True
        if not event.image_attachments:
            await actions.send_group_message(
                event.group_id,
                "图片理解需要和请求放在同一条消息里，请 @ 我并同时发送图片。",
            )
            return True
        if image_understanding is None:
            await actions.send_group_message(event.group_id, "图片理解当前不可用。")
            return True
        if image_budget is not None and not image_budget.try_consume(
            group_id=event.group_id,
            user_id=event.user_id,
            day=date.today(),
        ):
            await actions.send_group_message(event.group_id, "图片理解今日额度已用完。")
            return True
        try:
            reply = await image_understanding.describe(
                prompt=image_trigger.prompt,
                images=event.image_attachments,
                model=image_input_model,
            )
        except ImageUnderstandingDisabledError:
            await actions.send_group_message(event.group_id, "图片理解当前不可用，视觉模型尚未接入。")
            return True
        except Exception:
            logger.exception("Image understanding failed for group %s", event.group_id)
            return False
        if reply:
            if len(reply) > max_reply_chars:
                reply = reply[:max_reply_chars]
            await actions.send_group_message(event.group_id, reply)
        return True

    if message_text and memory is not None:
        memory.add_message(
            user_id=event.user_id,
            nickname=event.nickname,
            content=message_text,
        )
    if message_text and group_state_store is not None:
        await group_state_store.add_message(
            group_id=event.group_id,
            user_id=event.user_id,
            nickname=event.nickname,
            role="user",
            content=message_text,
        )
        await group_state_store.prune_messages(
            group_id=event.group_id,
            keep_latest=memory_max_messages,
        )

    # @ bot — trigger LLM reply
    if llm is not None and memory is not None and at_bot:
        if cooldown_limiter is not None and not cooldown_limiter.try_consume(
            group_id=event.group_id,
            user_id=event.user_id,
            now=datetime.now(tz=timezone.utc),
        ):
            logger.info("Cooldown hit for group %s user %s", event.group_id, event.user_id)
            return True

        search_context: list[str] = []
        search_trigger = detect_search_trigger(message_text)
        if (
            enable_web_search
            and search_trigger.should_search
            and search_trigger.query
            and web_search is not None
            and search_budget is not None
            and search_budget.try_consume(
                group_id=event.group_id,
                user_id=event.user_id,
                day=date.today(),
            )
        ):
            try:
                results = await web_search.search(
                    search_trigger.query,
                    max_results=search_max_results,
                )
            except SearchDisabledError:
                logger.info("Web search disabled for group %s", event.group_id)
            except Exception:
                logger.exception("Web search failed for group %s", event.group_id)
            else:
                search_context = [
                    f"来源 {index}: {result.title} - {result.snippet} {result.url}"
                    for index, result in enumerate(results, start=1)
                ]

        # Build prompt with recent context
        recent = memory.get_recent()
        messages = build_prompt(
            recent_context=recent[:-1],  # exclude the current message from context
            current_message=message_text,
            current_nickname=event.nickname,
            search_context=search_context,
        )

        # Call LLM
        try:
            reply = await llm.chat(messages)
        except Exception:
            logger.exception("LLM chat failed for group %s", event.group_id)
            return False

        if not reply:
            logger.info("LLM returned empty reply for group %s", event.group_id)
            return True  # handled (we saw the @), just nothing to say

        # Truncate if too long
        if len(reply) > max_reply_chars:
            reply = reply[:max_reply_chars]

        await actions.send_group_message(event.group_id, reply)

        # Record bot's own reply into context
        memory.add_message(
            user_id=bot_qq,
            nickname="bot",
            content=reply,
        )
        if group_state_store is not None:
            await group_state_store.add_message(
                group_id=event.group_id,
                user_id=bot_qq,
                nickname="bot",
                role="bot",
                content=reply,
            )
            await group_state_store.prune_messages(
                group_id=event.group_id,
                keep_latest=memory_max_messages,
            )

        logger.info(
            "LLM reply sent to group %s (%d chars)",
            event.group_id, len(reply),
        )
        return True

    return False
