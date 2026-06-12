from __future__ import annotations

import logging
from typing import Protocol

from qq_ai_bot.llm.prompt import build_prompt
from qq_ai_bot.memory.context import GroupMemory
from qq_ai_bot.onebot.events import GroupMessageEvent
from qq_ai_bot.onebot.utils import is_at_bot

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
) -> bool:
    if event.group_id != target_group_id:
        return False

    message_text = event.message.strip()

    # /bot ping — fixed reply, no LLM needed
    if message_text.startswith("/bot ping"):
        await actions.send_group_message(event.group_id, "pong")
        return True

    if memory is not None:
        memory.add_message(
            user_id=event.user_id,
            nickname=event.nickname,
            content=message_text,
        )

    # @ bot — trigger LLM reply
    if llm is not None and memory is not None and is_at_bot(event.message, bot_qq=bot_qq):
        # Build prompt with recent context
        recent = memory.get_recent()
        messages = build_prompt(
            recent_context=recent[:-1],  # exclude the current message from context
            current_message=message_text,
            current_nickname=event.nickname,
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
