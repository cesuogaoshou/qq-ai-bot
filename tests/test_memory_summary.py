from qq_ai_bot.memory.summary import build_recent_summary_prompt


def test_build_recent_summary_prompt_includes_recent_messages() -> None:
    prompt = build_recent_summary_prompt(
        [
            {"nickname": "Alice", "content": "我们决定先做 SQLite 消息存储"},
            {"nickname": "Bob", "content": "后面再做长期记忆"},
        ]
    )

    joined = "\n".join(message["content"] for message in prompt)

    assert "Alice: 我们决定先做 SQLite 消息存储" in joined
    assert "Bob: 后面再做长期记忆" in joined


def test_build_recent_summary_prompt_includes_privacy_constraints() -> None:
    prompt = build_recent_summary_prompt(
        [{"nickname": "Alice", "content": "帮我总结刚才聊天"}]
    )

    joined = "\n".join(message["content"] for message in prompt)

    assert "不要推断政治" in joined
    assert "不要暴露手机号" in joined
    assert "事实" in joined
    assert "待确认" in joined


def test_build_recent_summary_prompt_handles_empty_messages() -> None:
    prompt = build_recent_summary_prompt([])

    joined = "\n".join(message["content"] for message in prompt)

    assert "没有可总结的最近聊天记录" in joined
