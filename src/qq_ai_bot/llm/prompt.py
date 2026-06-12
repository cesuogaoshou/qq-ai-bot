from __future__ import annotations

from datetime import datetime, timezone

DEFAULT_PERSONA = (
    "你是这个 QQ 群里的轻量群友型助手。"
    "你的目标是让群聊更自然、更舒服，而不是抢话。"
    "平时回复要短，像普通群友。"
    "被 @ 或被请求帮忙时，可以认真回答，但不要写得太长。"
    "你可以轻微吐槽和接梗，但不能人身攻击。"
    "群里争吵时优先降温。"
    "不确定群内背景时先问一句，不要装懂。"
    "不要频繁说\u201c我是 AI\u201d。"
)

CURRENT_MESSAGE_TEMPLATE = "{nickname} @了你，说：{message}"


def _current_date_context() -> str:
    now = datetime.now(tz=timezone.utc).astimezone()
    return (
        f"当前时间是 {now.strftime('%Y年%m月%d日 %H:%M')} "
        f"（{now.strftime('%A')}），时区 {now.strftime('%Z')}。"
        "请不要说你不知道当前时间或你的知识截止于某个日期。"
    )

CURRENT_MESSAGE_TEMPLATE = "{nickname} @了你，说：{message}"


def build_prompt(
    *,
    recent_context: list[dict[str, str]],
    current_message: str,
    current_nickname: str,
) -> list[dict[str, str]]:
    """Construct the full message list for an LLM call.

    Structure: system persona → recent group context → current @ message.
    """
    system_content = f"{DEFAULT_PERSONA}\n\n{_current_date_context()}"
    messages: list[dict[str, str]] = [
        {"role": "system", "content": system_content},
    ]
    messages.extend(recent_context)
    messages.append(
        {
            "role": "user",
            "content": CURRENT_MESSAGE_TEMPLATE.format(
                nickname=current_nickname,
                message=current_message,
            ),
        }
    )
    return messages
