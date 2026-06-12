from __future__ import annotations


def build_recent_summary_prompt(messages: list[dict[str, str]]) -> list[dict[str, str]]:
    system_content = (
        "你是 QQ 群聊天总结助手。请用简短要点总结最近聊天。"
        "输出需要分为：事实、已决定事项、待确认事项。"
        "不要推断政治、宗教、健康、经济、感情、年龄、性别等敏感属性。"
        "不要暴露手机号、住址、身份证、银行卡等个人隐私。"
        "不要给群友贴负面人格标签。"
    )
    if not messages:
        return [
            {"role": "system", "content": system_content},
            {"role": "user", "content": "没有可总结的最近聊天记录。"},
        ]

    context = "\n".join(
        f"{message.get('nickname', 'unknown')}: {message.get('content', '')}"
        for message in messages
    )
    return [
        {"role": "system", "content": system_content},
        {"role": "user", "content": f"最近聊天记录：\n{context}"},
    ]
