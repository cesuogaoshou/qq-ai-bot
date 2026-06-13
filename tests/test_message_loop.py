import pytest

from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.memory.context import GroupMemory
from qq_ai_bot.memory.image_cache import RecentImageCache
from qq_ai_bot.onebot.events import GroupMessageEvent, ImageAttachment
from qq_ai_bot.policy.rate_limit import CooldownLimiter
from qq_ai_bot.services.message_loop import handle_group_message
from qq_ai_bot.storage.sqlite_store import GroupState, StoredMessage
from qq_ai_bot.tools.web_search import SearchResult


class FakeActions:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_group_message(self, group_id: int, message: str) -> None:
        self.sent.append((group_id, message))


class FakeLLM:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[list[dict[str, str]]] = []

    async def chat(self, messages: list[dict[str, str]]) -> str:
        self.calls.append(messages)
        return self.reply


class FakeSearchClient:
    def __init__(self) -> None:
        self.queries: list[tuple[str, int]] = []

    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        self.queries.append((query, max_results))
        return [
            SearchResult(
                title="豆包更新",
                url="https://example.com/doubao",
                snippet="今天发布了模型能力说明。",
            )
        ]


class FakeImageUnderstandingClient:
    def __init__(self, reply: str) -> None:
        self.reply = reply
        self.calls: list[dict[str, object]] = []

    async def describe(
        self,
        *,
        prompt: str,
        images: list[ImageAttachment],
        model: str,
    ) -> str:
        self.calls.append({"prompt": prompt, "images": images, "model": model})
        return self.reply


class FakeGroupStateStore:
    def __init__(self, enabled: bool = True) -> None:
        self.state = GroupState(group_id=123456, enabled=enabled, mode="mention_only")
        self.messages: list[StoredMessage] = []

    async def get_group(self, group_id: int) -> GroupState:
        return self.state

    async def set_enabled(self, group_id: int, enabled: bool) -> GroupState:
        self.state = GroupState(group_id=group_id, enabled=enabled, mode="mention_only")
        return self.state

    async def add_message(
        self,
        *,
        group_id: int,
        user_id: int,
        nickname: str,
        role: str,
        content: str,
    ) -> StoredMessage:
        message = StoredMessage(
            id=len(self.messages) + 1,
            group_id=group_id,
            user_id=user_id,
            nickname=nickname,
            role=role,
            content=content,
            created_at="2026-06-13T00:00:00+00:00",
        )
        self.messages.append(message)
        return message

    async def get_recent_messages(self, *, group_id: int, limit: int) -> list[StoredMessage]:
        return [message for message in self.messages if message.group_id == group_id][-limit:]

    async def count_messages(self, *, group_id: int) -> int:
        return len([message for message in self.messages if message.group_id == group_id])

    async def clear_messages(self, *, group_id: int) -> int:
        before = len(self.messages)
        self.messages = [message for message in self.messages if message.group_id != group_id]
        return before - len(self.messages)

    async def get_message_stats(self, *, group_id: int):
        from qq_ai_bot.storage.sqlite_store import MessageStats

        messages = [message for message in self.messages if message.group_id == group_id]
        if not messages:
            return MessageStats(count=0, oldest_created_at=None, newest_created_at=None)
        return MessageStats(
            count=len(messages),
            oldest_created_at=messages[0].created_at,
            newest_created_at=messages[-1].created_at,
        )

    async def prune_messages(self, *, group_id: int, keep_latest: int) -> int:
        if keep_latest <= 0:
            return 0
        target = [message for message in self.messages if message.group_id == group_id]
        keep_ids = {message.id for message in target[-keep_latest:]}
        before = len(self.messages)
        self.messages = [
            message
            for message in self.messages
            if message.group_id != group_id or message.id in keep_ids
        ]
        return before - len(self.messages)


@pytest.mark.anyio
async def test_replies_to_ping_in_target_group() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456, user_id=42, message=" /bot ping ", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions,
    )

    assert handled is True
    assert actions.sent == [(123456, "pong")]


@pytest.mark.anyio
async def test_ignores_other_groups() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=999999, user_id=42, message="/bot ping", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions,
    )

    assert handled is False
    assert actions.sent == []


@pytest.mark.anyio
async def test_at_bot_triggers_llm_reply() -> None:
    actions = FakeActions()

    memory = GroupMemory(max_messages=30)
    llm = FakeLLM("这是 LLM 的回复")
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=999] 你好啊", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
    )

    assert handled is True
    assert len(actions.sent) == 1
    assert actions.sent[0] == (123456, "这是 LLM 的回复")
    assert memory.get_recent() == [
        {"role": "user", "content": "Alice: [CQ:at,qq=999] 你好啊"},
        {"role": "user", "content": "bot: 这是 LLM 的回复"},
    ]


@pytest.mark.anyio
async def test_at_bot_llm_empty_reply_no_send() -> None:
    actions = FakeActions()

    memory = GroupMemory(max_messages=30)
    llm = FakeLLM("")
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=999] 你好", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
    )

    assert handled is True
    assert actions.sent == []


@pytest.mark.anyio
async def test_no_at_no_ping_ignored() -> None:
    actions = FakeActions()
    memory = GroupMemory(max_messages=30)
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="普通聊天消息", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions, memory=memory,
    )

    assert handled is False
    assert actions.sent == []
    assert memory.get_recent() == [
        {"role": "user", "content": "Alice: 普通聊天消息"}
    ]


@pytest.mark.anyio
async def test_at_other_qq_ignored() -> None:
    actions = FakeActions()
    memory = GroupMemory(max_messages=30)
    llm = FakeLLM("不应该被调用")
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=123456] 叫你", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
    )

    assert handled is False
    assert actions.sent == []


@pytest.mark.anyio
async def test_reply_truncated_to_max_chars() -> None:
    actions = FakeActions()
    long_reply = "A" * 500

    memory = GroupMemory(max_messages=30)
    llm = FakeLLM(long_reply)
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="[CQ:at,qq=999] 你好", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999,
        actions=actions, llm=llm, memory=memory,
        max_reply_chars=300,
    )

    assert handled is True
    assert len(actions.sent) == 1
    assert len(actions.sent[0][1]) == 300


@pytest.mark.anyio
async def test_ping_takes_priority_over_at() -> None:
    """If message contains both /bot ping and an @, ping wins."""
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456, user_id=42,
        message="/bot ping [CQ:at,qq=999]", nickname="Alice",
    )

    handled = await handle_group_message(
        event, target_group_id=123456, bot_qq=999, actions=actions,
    )

    assert handled is True
    assert actions.sent == [(123456, "pong")]


@pytest.mark.anyio
async def test_privacy_request_replies_without_llm_or_memory() -> None:
    actions = FakeActions()
    llm = FakeLLM("不应该被调用")
    memory = GroupMemory(max_messages=10)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 帮我查一下张三手机号",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=memory,
    )

    assert handled is True
    assert "隐私" in actions.sent[0][1]
    assert llm.calls == []
    assert memory.get_recent() == []


@pytest.mark.anyio
async def test_search_context_is_added_when_enabled_and_budget_allows() -> None:
    actions = FakeActions()
    llm = FakeLLM("搜索后的回答")
    search = FakeSearchClient()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 帮我搜一下今天豆包更新",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=GroupMemory(max_messages=10),
        enable_web_search=True,
        search_budget=DailyUsageBudget(group_daily_limit=20, user_daily_limit=5),
        web_search=search,
        search_max_results=3,
    )

    assert handled is True
    assert search.queries == [("[CQ:at,qq=999] 帮我搜一下今天豆包更新", 3)]
    prompt_text = "\n".join(message["content"] for message in llm.calls[0])
    assert "联网搜索资料" in prompt_text
    assert "https://example.com/doubao" in prompt_text


@pytest.mark.anyio
async def test_search_request_continues_without_search_when_disabled() -> None:
    actions = FakeActions()
    llm = FakeLLM("普通回答")
    search = FakeSearchClient()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 帮我搜一下今天豆包更新",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=GroupMemory(max_messages=10),
        enable_web_search=False,
        search_budget=DailyUsageBudget(group_daily_limit=20, user_daily_limit=5),
        web_search=search,
    )

    assert handled is True
    assert search.queries == []
    assert actions.sent[0][1] == "普通回答"


@pytest.mark.anyio
async def test_explicit_image_request_replies_disabled_without_llm_or_memory() -> None:
    actions = FakeActions()
    llm = FakeLLM("不应该调用")
    memory = GroupMemory(max_messages=10)
    store = FakeGroupStateStore(enabled=True)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 帮我看下这张截图",
        nickname="Alice",
        image_attachments=[
            ImageAttachment(file="abc.image", url="http://example.com/a.jpg")
        ],
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=memory,
        group_state_store=store,
        enable_image_input=False,
    )

    assert handled is True
    assert "图片理解当前未开启" in actions.sent[0][1]
    assert llm.calls == []
    assert memory.get_recent() == []
    assert store.messages == []


@pytest.mark.anyio
async def test_image_capability_question_replies_disabled_without_llm() -> None:
    actions = FakeActions()
    llm = FakeLLM("不应该说自己能看图")
    memory = GroupMemory(max_messages=10)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 你能看图吗",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=memory,
        enable_image_input=False,
    )

    assert handled is True
    assert "图片理解当前未开启" in actions.sent[0][1]
    assert llm.calls == []
    assert memory.get_recent() == []


@pytest.mark.anyio
async def test_image_ocr_request_without_same_message_image_replies_disabled_without_llm() -> None:
    actions = FakeActions()
    llm = FakeLLM("不应该让用户重发图片")
    memory = GroupMemory(max_messages=10)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 提取图中文字",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=memory,
        enable_image_input=False,
    )

    assert handled is True
    assert "图片理解当前未开启" in actions.sent[0][1]
    assert llm.calls == []
    assert memory.get_recent() == []


@pytest.mark.anyio
async def test_explicit_image_request_uses_image_client_when_enabled() -> None:
    actions = FakeActions()
    image_client = FakeImageUnderstandingClient("图片里是一段错误日志。")
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 帮我看图",
        nickname="Alice",
        image_attachments=[
            ImageAttachment(file="abc.image", url="http://example.com/a.jpg")
        ],
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        memory=GroupMemory(max_messages=10),
        enable_image_input=True,
        image_budget=DailyUsageBudget(group_daily_limit=5, user_daily_limit=5),
        image_understanding=image_client,
        image_input_model="doubao-vision-test",
    )

    assert handled is True
    assert actions.sent == [(123456, "图片里是一段错误日志。")]
    assert len(image_client.calls) == 1
    assert image_client.calls[0]["prompt"] == "[CQ:at,qq=999] 帮我看图"
    assert image_client.calls[0]["model"] == "doubao-vision-test"


@pytest.mark.anyio
async def test_image_request_replies_when_image_client_returns_empty() -> None:
    actions = FakeActions()
    image_client = FakeImageUnderstandingClient("")
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="[CQ:at,qq=999] 提取图中文字",
        nickname="Alice",
        image_attachments=[
            ImageAttachment(file="abc.image", url="http://example.com/a.jpg")
        ],
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        memory=GroupMemory(max_messages=10),
        enable_image_input=True,
        image_budget=DailyUsageBudget(group_daily_limit=5, user_daily_limit=5),
        image_understanding=image_client,
        image_input_model="doubao-seed-2.0-lite",
    )

    assert handled is True
    assert actions.sent == [(123456, "图片理解调用失败或没有返回内容，请稍后再试。")]


@pytest.mark.anyio
async def test_image_request_uses_recent_user_image_cache_when_enabled() -> None:
    actions = FakeActions()
    image_client = FakeImageUnderstandingClient("缓存图片里有文字。")
    image_cache = RecentImageCache(max_entries=5)

    first = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="",
            nickname="Alice",
            image_attachments=[
                ImageAttachment(file="abc.image", url="http://example.com/a.jpg")
            ],
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        image_cache=image_cache,
    )
    second = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="[CQ:at,qq=999] 提取图中文字",
            nickname="Alice",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        memory=GroupMemory(max_messages=10),
        enable_image_input=True,
        image_budget=DailyUsageBudget(group_daily_limit=5, user_daily_limit=5),
        image_understanding=image_client,
        image_input_model="doubao-vision-test",
        image_cache=image_cache,
    )

    assert first is False
    assert second is True
    assert actions.sent == [(123456, "缓存图片里有文字。")]
    assert image_client.calls[0]["images"] == [
        ImageAttachment(file="abc.image", url="http://example.com/a.jpg")
    ]


@pytest.mark.anyio
async def test_admin_can_turn_bot_off() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="/bot off",
        nickname="Admin",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=store,
        admin_qq_ids={42},
    )

    assert handled is True
    assert store.state.enabled is False
    assert actions.sent == [(123456, "机器人已关闭。")]


@pytest.mark.anyio
async def test_non_admin_cannot_turn_bot_off() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=7,
        message="/bot off",
        nickname="Bob",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=store,
        admin_qq_ids={42},
    )

    assert handled is True
    assert store.state.enabled is True
    assert actions.sent == [(123456, "你没有权限执行这个命令。")]


@pytest.mark.anyio
async def test_disabled_group_suppresses_llm_reply() -> None:
    actions = FakeActions()
    llm = FakeLLM("不应该发送")
    event = GroupMessageEvent(
        group_id=123456,
        user_id=7,
        message="[CQ:at,qq=999] 你好",
        nickname="Bob",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=GroupMemory(max_messages=10),
        group_state_store=FakeGroupStateStore(enabled=False),
    )

    assert handled is True
    assert llm.calls == []
    assert actions.sent == []


@pytest.mark.anyio
async def test_admin_can_turn_bot_on_after_disabled() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=False)
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="/bot on",
        nickname="Admin",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=store,
        admin_qq_ids={42},
    )

    assert handled is True
    assert store.state.enabled is True
    assert actions.sent == [(123456, "机器人已开启。")]


@pytest.mark.anyio
async def test_admin_status_includes_runtime_state() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="/bot status",
        nickname="Admin",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=FakeGroupStateStore(enabled=True),
        admin_qq_ids={42},
        enable_web_search=False,
        group_cooldown_seconds=20,
        user_cooldown_seconds=10,
    )

    assert handled is True
    assert "enabled=True" in actions.sent[0][1]
    assert "mode=mention_only" in actions.sent[0][1]
    assert "web_search=False" in actions.sent[0][1]
    assert "group_cooldown=20s" in actions.sent[0][1]
    assert "user_cooldown=10s" in actions.sent[0][1]


@pytest.mark.anyio
async def test_cooldown_blocks_second_llm_call() -> None:
    actions = FakeActions()
    llm = FakeLLM("回复")
    limiter = CooldownLimiter(group_cooldown_seconds=20, user_cooldown_seconds=10)
    memory = GroupMemory(max_messages=10)

    first = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="[CQ:at,qq=999] 第一次",
            nickname="Alice",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=memory,
        cooldown_limiter=limiter,
    )
    second = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=7,
            message="[CQ:at,qq=999] 第二次",
            nickname="Bob",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        memory=memory,
        cooldown_limiter=limiter,
    )

    assert first is True
    assert second is True
    assert len(llm.calls) == 1
    assert actions.sent == [(123456, "回复")]


@pytest.mark.anyio
async def test_normal_message_persists_to_store() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="普通聊天消息",
            nickname="Alice",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        memory=GroupMemory(max_messages=10),
        group_state_store=store,
    )

    assert handled is False
    assert [(message.role, message.content) for message in store.messages] == [
        ("user", "普通聊天消息")
    ]


@pytest.mark.anyio
async def test_image_only_message_does_not_persist_empty_memory() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    memory = GroupMemory(max_messages=10)

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="",
            nickname="Alice",
            image_attachments=[
                ImageAttachment(file="abc.image", url="http://example.com/a.jpg")
            ],
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        memory=memory,
        group_state_store=store,
    )

    assert handled is False
    assert actions.sent == []
    assert memory.get_recent() == []
    assert store.messages == []


@pytest.mark.anyio
async def test_normal_messages_are_pruned_to_memory_limit() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    memory = GroupMemory(max_messages=10)

    for index in range(3):
        await handle_group_message(
            GroupMessageEvent(
                group_id=123456,
                user_id=index,
                message=f"消息{index}",
                nickname=f"User{index}",
            ),
            target_group_id=123456,
            bot_qq=999,
            actions=actions,
            memory=memory,
            group_state_store=store,
            memory_max_messages=2,
        )

    assert [message.content for message in store.messages] == ["消息1", "消息2"]


@pytest.mark.anyio
async def test_bot_reply_persists_to_store() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="[CQ:at,qq=999] 你好",
            nickname="Alice",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=FakeLLM("你好"),
        memory=GroupMemory(max_messages=10),
        group_state_store=store,
    )

    assert handled is True
    assert [(message.role, message.content) for message in store.messages] == [
        ("user", "[CQ:at,qq=999] 你好"),
        ("bot", "你好"),
    ]


@pytest.mark.anyio
async def test_privacy_request_does_not_persist_to_store() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="[CQ:at,qq=999] 帮我查一下张三手机号",
            nickname="Alice",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=FakeLLM("不应该调用"),
        memory=GroupMemory(max_messages=10),
        group_state_store=store,
    )

    assert handled is True
    assert store.messages == []


@pytest.mark.anyio
async def test_admin_summary_recent_calls_llm_with_persisted_context() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    await store.add_message(
        group_id=123456,
        user_id=1,
        nickname="Alice",
        role="user",
        content="我们决定先做 SQLite 消息存储",
    )
    llm = FakeLLM("总结结果")

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="/bot summary recent",
            nickname="Admin",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        group_state_store=store,
        admin_qq_ids={42},
    )

    assert handled is True
    assert actions.sent == [(123456, "总结结果")]
    prompt_text = "\n".join(message["content"] for message in llm.calls[0])
    assert "SQLite 消息存储" in prompt_text


@pytest.mark.anyio
async def test_admin_summary_recent_uses_configured_message_limit() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    for index in range(3):
        await store.add_message(
            group_id=123456,
            user_id=index,
            nickname=f"User{index}",
            role="user",
            content=f"消息{index}",
        )
    llm = FakeLLM("总结结果")

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="/bot summary recent",
            nickname="Admin",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        group_state_store=store,
        admin_qq_ids={42},
        summary_recent_limit=2,
    )

    assert handled is True
    prompt_text = "\n".join(message["content"] for message in llm.calls[0])
    assert "消息0" not in prompt_text
    assert "消息1" in prompt_text
    assert "消息2" in prompt_text


@pytest.mark.anyio
async def test_admin_summary_recent_reply_truncated_to_max_chars() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    await store.add_message(
        group_id=123456,
        user_id=1,
        nickname="Alice",
        role="user",
        content="需要总结的消息",
    )
    llm = FakeLLM("A" * 500)

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="/bot summary recent",
            nickname="Admin",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        llm=llm,
        group_state_store=store,
        admin_qq_ids={42},
        max_reply_chars=120,
    )

    assert handled is True
    assert len(actions.sent) == 1
    assert len(actions.sent[0][1]) == 120


@pytest.mark.anyio
async def test_summary_recent_without_llm_replies_unavailable() -> None:
    actions = FakeActions()

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="/bot summary recent",
            nickname="Admin",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=FakeGroupStateStore(enabled=True),
        admin_qq_ids={42},
    )

    assert handled is True
    assert actions.sent == [(123456, "当前未配置大模型，无法生成聊天总结。")]


@pytest.mark.anyio
async def test_memory_status_includes_message_count() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    await store.add_message(
        group_id=123456,
        user_id=1,
        nickname="Alice",
        role="user",
        content="一条消息",
    )

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="/bot memory status",
            nickname="Admin",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=store,
        admin_qq_ids={42},
    )

    assert handled is True
    assert "messages=1" in actions.sent[0][1]
    assert "oldest=2026-06-13T00:00:00+00:00" in actions.sent[0][1]
    assert "newest=2026-06-13T00:00:00+00:00" in actions.sent[0][1]


@pytest.mark.anyio
async def test_memory_clear_removes_messages() -> None:
    actions = FakeActions()
    store = FakeGroupStateStore(enabled=True)
    await store.add_message(
        group_id=123456,
        user_id=1,
        nickname="Alice",
        role="user",
        content="一条消息",
    )

    handled = await handle_group_message(
        GroupMessageEvent(
            group_id=123456,
            user_id=42,
            message="/bot memory clear",
            nickname="Admin",
        ),
        target_group_id=123456,
        bot_qq=999,
        actions=actions,
        group_state_store=store,
        admin_qq_ids={42},
    )

    assert handled is True
    assert store.messages == []
    assert actions.sent == [(123456, "已清理 1 条聊天记忆。")]
