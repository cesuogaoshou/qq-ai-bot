from qq_ai_bot.llm.prompt import build_prompt


def test_build_prompt_includes_search_results_when_present() -> None:
    messages = build_prompt(
        recent_context=[
            {"role": "user", "content": "Alice: 刚才聊模型更新"},
        ],
        current_message="帮我查一下今天豆包有什么更新",
        current_nickname="Alice",
        search_context=[
            "来源 1: 火山方舟文档 - 豆包模型能力更新摘要 https://example.com/doubao",
        ],
    )

    joined = "\n".join(message["content"] for message in messages)
    assert "联网搜索资料" in joined
    assert "来源 1" in joined
    assert "https://example.com/doubao" in joined
