from __future__ import annotations

import logging
from datetime import date
from typing import Protocol

from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.llm.prompt import build_prompt
from qq_ai_bot.memory.context import GroupMemory
from qq_ai_bot.onebot.events import GroupMessageEvent
from qq_ai_bot.onebot.utils import is_at_bot
from qq_ai_bot.policy.safety import SafetyAction, classify_message_safety
from qq_ai_bot.policy.tool_trigger import detect_search_trigger
from qq_ai_bot.tools.web_search import SearchDisabledError, WebSearchClient

logger = logging.getLogger(__name__)


class GroupMessageActions(Protocol):
    async def send_group_message(self, group_id: int, message: str) -> None:
        ...


class LLMChat(Protocol):
    async def chat(self, messages: list[dict[str, str]]) -> str:
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
) -> bool:
    if event.group_id != target_group_id:
        return False

    message_text = event.message.strip()

    # /bot ping — fixed reply, no LLM needed
    if message_text.startswith("/bot ping"):
        await actions.send_group_message(event.group_id, "pong")
        return True

    at_bot = is_at_bot(event.message, bot_qq=bot_qq)
    safety = classify_message_safety(message_text)
    if safety.action in {SafetyAction.DEESCALATE, SafetyAction.REFUSE} and at_bot:
        if safety.reply:
            await actions.send_group_message(event.group_id, safety.reply)
        return True

    if memory is not None:
        memory.add_message(
            user_id=event.user_id,
            nickname=event.nickname,
            content=message_text,
        )

    # @ bot — trigger LLM reply
    if llm is not None and memory is not None and at_bot:
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

        logger.info(
            "LLM reply sent to group %s (%d chars)",
            event.group_id, len(reply),
        )
        return True

    return False
