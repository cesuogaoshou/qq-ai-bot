from qq_ai_bot.llm.prompt import build_prompt, sanitize_cq_codes


def test_sanitize_cq_codes_removes_at_and_image_segments() -> None:
    assert (
        sanitize_cq_codes("[CQ:at,qq=3885518851] 今天天气怎么样 [CQ:image,file=a.jpg]")
        == "今天天气怎么样"
    )


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


def test_build_prompt_strips_cq_codes_from_current_and_recent_context() -> None:
    messages = build_prompt(
        recent_context=[
            {"role": "user", "content": "Alice: [CQ:at,qq=3885518851] 你好"},
        ],
        current_message="[CQ:at,qq=3885518851] 今天天气怎么样 [CQ:image,file=a.jpg]",
        current_nickname="Alice",
    )

    joined = "\n".join(message["content"] for message in messages)
    assert "[CQ:" not in joined
    assert "今天天气怎么样" in joined
