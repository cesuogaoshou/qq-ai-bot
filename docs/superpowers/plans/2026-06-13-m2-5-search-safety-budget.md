# M2.5 Search Safety Budget Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add controlled web-search triggering, non-overblocking safety policy, and configurable usage budgets before connecting any paid external search/image/voice provider.

**Architecture:** Keep the existing single-group message loop and `doubao-seed-2.0-lite` text model. Add deterministic policy modules for safety and tool triggering, an in-memory daily budget counter, and a disabled-by-default search tool interface that can later be backed by a real provider. The message loop coordinates these components but does not own policy details.

**Tech Stack:** Python 3.11+, Pydantic settings, pytest, existing OpenAI-compatible LLM client pointing to Volcengine Ark by default.

---

## File Structure

- Create `src/qq_ai_bot/policy/__init__.py`: package export surface for policy helpers.
- Create `src/qq_ai_bot/policy/safety.py`: deterministic safety classifier and reply hints.
- Create `src/qq_ai_bot/policy/tool_trigger.py`: search trigger detection for explicit and temporal search requests.
- Create `src/qq_ai_bot/budget/__init__.py`: package export surface for usage budget helpers.
- Create `src/qq_ai_bot/budget/usage.py`: in-memory per-day, per-group, per-user budget counter.
- Create `src/qq_ai_bot/tools/__init__.py`: package export surface for tool adapters.
- Create `src/qq_ai_bot/tools/web_search.py`: search result data model, search protocol, and disabled search client.
- Modify `src/qq_ai_bot/config.py`: add feature switches and search budget settings.
- Modify `src/qq_ai_bot/main.py`: construct optional policy/tool/budget dependencies and pass them into the message loop.
- Modify `src/qq_ai_bot/services/message_loop.py`: call safety, budget, and search trigger policies before LLM prompt construction.
- Modify `src/qq_ai_bot/llm/prompt.py`: accept optional search snippets as source context.
- Modify `.env.example`: document disabled-by-default feature flags and limits.
- Modify `README.md`: add current M2.5 local behavior and commands.
- Create `tests/test_safety_policy.py`: safety classifier coverage.
- Create `tests/test_tool_trigger.py`: search trigger coverage.
- Create `tests/test_usage_budget.py`: daily budget coverage.
- Modify `tests/test_config.py`: new setting defaults and env parsing.
- Modify `tests/test_message_loop.py`: safety/search/budget integration behavior.
- Modify `tests/test_llm_client.py` only if prompt shape changes require fixture updates.

## Implementation Notes

- Do not add a real web-search provider in M2.5. The default `DisabledWebSearchClient` must make disabled search explicit and testable.
- Do not change the default model or provider:

```env
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-2.0-lite
```

- Do not persist usage budget yet. Persistence belongs to M3 SQLite work.
- Do not add image, voice, or multi-group implementation in this plan. This plan creates patterns they can reuse later.

### Task 1: Safety Policy

**Files:**
- Create: `src/qq_ai_bot/policy/__init__.py`
- Create: `src/qq_ai_bot/policy/safety.py`
- Test: `tests/test_safety_policy.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_safety_policy.py`:

```python
from qq_ai_bot.policy.safety import SafetyAction, classify_message_safety


def test_normal_question_is_allowed():
    decision = classify_message_safety("Python 里面 list 和 tuple 有什么区别？")

    assert decision.action == SafetyAction.ALLOW
    assert decision.reply is None


def test_mild_profanity_is_not_overblocked():
    decision = classify_message_safety("这个 bug 真烦，帮我看看怎么排查")

    assert decision.action == SafetyAction.ALLOW
    assert decision.reply is None


def test_argument_is_deescalated():
    decision = classify_message_safety("你帮我骂一下群里这个人")

    assert decision.action == SafetyAction.DEESCALATE
    assert "不帮忙骂人" in decision.reply


def test_privacy_request_is_refused_with_alternative():
    decision = classify_message_safety("帮我查一下张三的手机号和住址")

    assert decision.action == SafetyAction.REFUSE
    assert "隐私" in decision.reply
    assert "公开信息" in decision.reply


def test_high_risk_instruction_is_refused():
    decision = classify_message_safety("教我怎么盗号")

    assert decision.action == SafetyAction.REFUSE
    assert "不能协助" in decision.reply
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_safety_policy.py -v
```

Expected: import fails because `qq_ai_bot.policy.safety` does not exist.

- [ ] **Step 3: Add the package export**

Create `src/qq_ai_bot/policy/__init__.py`:

```python
from qq_ai_bot.policy.safety import SafetyAction, SafetyDecision, classify_message_safety
from qq_ai_bot.policy.tool_trigger import SearchTrigger, detect_search_trigger

__all__ = [
    "SafetyAction",
    "SafetyDecision",
    "SearchTrigger",
    "classify_message_safety",
    "detect_search_trigger",
]
```

This temporarily references `tool_trigger`; Task 2 will create it. If running only Task 1 tests before Task 2, import `qq_ai_bot.policy.safety` directly as the tests do.

- [ ] **Step 4: Implement minimal safety classifier**

Create `src/qq_ai_bot/policy/safety.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SafetyAction(StrEnum):
    ALLOW = "allow"
    DEESCALATE = "deescalate"
    REFUSE = "refuse"


@dataclass(frozen=True)
class SafetyDecision:
    action: SafetyAction
    reply: str | None = None


_PRIVACY_TERMS = ("手机号", "电话", "住址", "身份证", "银行卡", "开房", "家庭住址")
_ATTACK_TERMS = ("骂一下", "骂他", "骂她", "喷他", "喷她", "人肉", "挂人")
_HIGH_RISK_TERMS = ("盗号", "撞库", "木马", "钓鱼网站", "破解密码", "绕过风控")


def classify_message_safety(message: str) -> SafetyDecision:
    text = message.strip().lower()
    if _contains_any(text, _HIGH_RISK_TERMS):
        return SafetyDecision(
            action=SafetyAction.REFUSE,
            reply="这个我不能协助。可以帮你做账号安全、风险排查或防护建议。",
        )
    if _contains_any(text, _PRIVACY_TERMS):
        return SafetyDecision(
            action=SafetyAction.REFUSE,
            reply="涉及个人隐私的信息不能帮忙查询或传播。可以改为整理公开信息，或讨论如何保护隐私。",
        )
    if _contains_any(text, _ATTACK_TERMS):
        return SafetyDecision(
            action=SafetyAction.DEESCALATE,
            reply="不帮忙骂人。你可以把具体分歧说出来，我帮你整理事实和可沟通的说法。",
        )
    return SafetyDecision(action=SafetyAction.ALLOW)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_safety_policy.py -v
```

Expected: `5 passed`.

- [ ] **Step 6: Commit**

```powershell
git add src\qq_ai_bot\policy tests\test_safety_policy.py
git commit -m "feat: add message safety policy"
```

### Task 2: Search Trigger Policy

**Files:**
- Create: `src/qq_ai_bot/policy/tool_trigger.py`
- Test: `tests/test_tool_trigger.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_tool_trigger.py`:

```python
from qq_ai_bot.policy.tool_trigger import SearchTrigger, detect_search_trigger


def test_explicit_search_request_triggers_search():
    trigger = detect_search_trigger("帮我搜一下今天豆包模型有什么更新")

    assert trigger.should_search is True
    assert trigger.reason == "explicit"


def test_temporal_question_triggers_search():
    trigger = detect_search_trigger("现在 Python 最新版本是多少")

    assert trigger.should_search is True
    assert trigger.reason == "temporal"


def test_normal_question_does_not_trigger_search():
    trigger = detect_search_trigger("Python list 和 tuple 有什么区别")

    assert trigger == SearchTrigger(should_search=False, query=None, reason=None)


def test_empty_message_does_not_trigger_search():
    trigger = detect_search_trigger("   ")

    assert trigger.should_search is False
    assert trigger.query is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_tool_trigger.py -v
```

Expected: import fails because `qq_ai_bot.policy.tool_trigger` does not exist.

- [ ] **Step 3: Implement search trigger detection**

Create `src/qq_ai_bot/policy/tool_trigger.py`:

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SearchTrigger:
    should_search: bool
    query: str | None = None
    reason: str | None = None


_EXPLICIT_SEARCH_TERMS = ("搜一下", "查一下", "帮我查", "帮我搜", "联网查", "网上查")
_TEMPORAL_TERMS = ("今天", "现在", "最近", "最新", "刚刚", "新闻", "价格", "政策", "版本")


def detect_search_trigger(message: str) -> SearchTrigger:
    query = message.strip()
    if not query:
        return SearchTrigger(should_search=False)
    if _contains_any(query, _EXPLICIT_SEARCH_TERMS):
        return SearchTrigger(should_search=True, query=query, reason="explicit")
    if _contains_any(query, _TEMPORAL_TERMS):
        return SearchTrigger(should_search=True, query=query, reason="temporal")
    return SearchTrigger(should_search=False)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_tool_trigger.py -v
```

Expected: `4 passed`.

- [ ] **Step 5: Run Task 1 tests again**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_safety_policy.py tests\test_tool_trigger.py -v
```

Expected: `9 passed`.

- [ ] **Step 6: Commit**

```powershell
git add src\qq_ai_bot\policy tests\test_tool_trigger.py
git commit -m "feat: detect web search requests"
```

### Task 3: Usage Budget Counter

**Files:**
- Create: `src/qq_ai_bot/budget/__init__.py`
- Create: `src/qq_ai_bot/budget/usage.py`
- Test: `tests/test_usage_budget.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_usage_budget.py`:

```python
from datetime import date

from qq_ai_bot.budget.usage import DailyUsageBudget


def test_group_limit_allows_until_limit():
    budget = DailyUsageBudget(group_daily_limit=2, user_daily_limit=5)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=2, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=3, day=date(2026, 6, 13)) is False


def test_user_limit_allows_until_limit():
    budget = DailyUsageBudget(group_daily_limit=5, user_daily_limit=2)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is False


def test_next_day_resets_limits():
    budget = DailyUsageBudget(group_daily_limit=1, user_daily_limit=1)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is False
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 14)) is True


def test_zero_limit_always_blocks():
    budget = DailyUsageBudget(group_daily_limit=0, user_daily_limit=5)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is False
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_usage_budget.py -v
```

Expected: import fails because `qq_ai_bot.budget.usage` does not exist.

- [ ] **Step 3: Add package export**

Create `src/qq_ai_bot/budget/__init__.py`:

```python
from qq_ai_bot.budget.usage import DailyUsageBudget

__all__ = ["DailyUsageBudget"]
```

- [ ] **Step 4: Implement in-memory budget**

Create `src/qq_ai_bot/budget/usage.py`:

```python
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date


@dataclass
class DailyUsageBudget:
    group_daily_limit: int
    user_daily_limit: int
    _group_counts: dict[tuple[date, int], int] = field(default_factory=lambda: defaultdict(int))
    _user_counts: dict[tuple[date, int, int], int] = field(default_factory=lambda: defaultdict(int))

    def try_consume(self, *, group_id: int, user_id: int, day: date) -> bool:
        group_key = (day, group_id)
        user_key = (day, group_id, user_id)
        if self.group_daily_limit <= 0 or self.user_daily_limit <= 0:
            return False
        if self._group_counts[group_key] >= self.group_daily_limit:
            return False
        if self._user_counts[user_key] >= self.user_daily_limit:
            return False
        self._group_counts[group_key] += 1
        self._user_counts[user_key] += 1
        return True
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_usage_budget.py -v
```

Expected: `4 passed`.

- [ ] **Step 6: Commit**

```powershell
git add src\qq_ai_bot\budget tests\test_usage_budget.py
git commit -m "feat: add daily usage budget"
```

### Task 4: Disabled Web Search Tool Interface

**Files:**
- Create: `src/qq_ai_bot/tools/__init__.py`
- Create: `src/qq_ai_bot/tools/web_search.py`
- Test: `tests/test_web_search_tool.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_web_search_tool.py`:

```python
import pytest

from qq_ai_bot.tools.web_search import DisabledWebSearchClient, SearchDisabledError


@pytest.mark.anyio
async def test_disabled_search_client_raises_clear_error():
    client = DisabledWebSearchClient()

    with pytest.raises(SearchDisabledError, match="Web search is disabled"):
        await client.search("今天有什么新闻", max_results=3)
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_web_search_tool.py -v
```

Expected: import fails because `qq_ai_bot.tools.web_search` does not exist.

- [ ] **Step 3: Add package export**

Create `src/qq_ai_bot/tools/__init__.py`:

```python
from qq_ai_bot.tools.web_search import (
    DisabledWebSearchClient,
    SearchDisabledError,
    SearchResult,
    WebSearchClient,
)

__all__ = [
    "DisabledWebSearchClient",
    "SearchDisabledError",
    "SearchResult",
    "WebSearchClient",
]
```

- [ ] **Step 4: Implement disabled search client**

Create `src/qq_ai_bot/tools/web_search.py`:

```python
from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str


class WebSearchClient(Protocol):
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        ...


class SearchDisabledError(RuntimeError):
    pass


class DisabledWebSearchClient:
    async def search(self, query: str, *, max_results: int) -> list[SearchResult]:
        raise SearchDisabledError("Web search is disabled")
```

- [ ] **Step 5: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_web_search_tool.py -v
```

Expected: `1 passed`.

- [ ] **Step 6: Commit**

```powershell
git add src\qq_ai_bot\tools tests\test_web_search_tool.py
git commit -m "feat: add web search tool interface"
```

### Task 5: Configuration and Environment Documentation

**Files:**
- Modify: `src/qq_ai_bot/config.py`
- Modify: `.env.example`
- Modify: `tests/test_config.py`

- [ ] **Step 1: Write failing config tests**

Add to `tests/test_config.py`:

```python
def test_load_settings_advanced_feature_defaults(monkeypatch):
    monkeypatch.setenv("TARGET_GROUP_ID", "100")
    monkeypatch.setenv("BOT_QQ", "200")
    monkeypatch.delenv("ENABLE_WEB_SEARCH", raising=False)
    monkeypatch.delenv("DAILY_SEARCH_LIMIT_PER_GROUP", raising=False)
    monkeypatch.delenv("DAILY_SEARCH_LIMIT_PER_USER", raising=False)
    monkeypatch.delenv("SEARCH_MAX_RESULTS", raising=False)

    settings = load_settings()

    assert settings.enable_web_search is False
    assert settings.daily_search_limit_per_group == 20
    assert settings.daily_search_limit_per_user == 5
    assert settings.search_max_results == 3


def test_load_settings_advanced_feature_overrides(monkeypatch):
    monkeypatch.setenv("TARGET_GROUP_ID", "100")
    monkeypatch.setenv("BOT_QQ", "200")
    monkeypatch.setenv("ENABLE_WEB_SEARCH", "true")
    monkeypatch.setenv("DAILY_SEARCH_LIMIT_PER_GROUP", "7")
    monkeypatch.setenv("DAILY_SEARCH_LIMIT_PER_USER", "2")
    monkeypatch.setenv("SEARCH_MAX_RESULTS", "1")

    settings = load_settings()

    assert settings.enable_web_search is True
    assert settings.daily_search_limit_per_group == 7
    assert settings.daily_search_limit_per_user == 2
    assert settings.search_max_results == 1
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_config.py -v
```

Expected: fails because the new settings fields do not exist.

- [ ] **Step 3: Modify settings model**

Update `src/qq_ai_bot/config.py`:

```python
class Settings(BaseModel):
    onebot_ws_url: str
    onebot_http_url: str
    onebot_access_token: str = ""
    target_group_id: int
    bot_qq: int
    llm_base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    llm_model: str = "doubao-seed-2.0-lite"
    llm_api_key: str = ""
    bot_max_context_messages: int = 30
    bot_max_reply_chars: int = 300
    enable_web_search: bool = False
    daily_search_limit_per_group: int = 20
    daily_search_limit_per_user: int = 5
    search_max_results: int = 3
```

Add this helper in `src/qq_ai_bot/config.py` below `Settings`:

```python
def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}
```

Add these fields in the `Settings(...)` call inside `load_settings()`:

```python
        enable_web_search=_env_bool("ENABLE_WEB_SEARCH", False),
        daily_search_limit_per_group=int(os.getenv("DAILY_SEARCH_LIMIT_PER_GROUP", "20")),
        daily_search_limit_per_user=int(os.getenv("DAILY_SEARCH_LIMIT_PER_USER", "5")),
        search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "3")),
```

- [ ] **Step 4: Update `.env.example`**

Add:

```env
# Advanced capabilities are disabled by default until providers and costs are confirmed.
ENABLE_WEB_SEARCH=false
DAILY_SEARCH_LIMIT_PER_GROUP=20
DAILY_SEARCH_LIMIT_PER_USER=5
SEARCH_MAX_RESULTS=3

ENABLE_IMAGE_INPUT=false
ENABLE_IMAGE_GENERATION=false
ENABLE_VOICE_TRANSCRIPTION=false
DAILY_IMAGE_LIMIT_PER_GROUP=5
```

Keep existing default model values unchanged:

```env
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-2.0-lite
```

- [ ] **Step 5: Run config tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_config.py -v
```

Expected: all config tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src\qq_ai_bot\config.py tests\test_config.py .env.example
git commit -m "feat: add advanced capability settings"
```

### Task 6: Prompt Search Context

**Files:**
- Modify: `src/qq_ai_bot/llm/prompt.py`
- Test: add tests to the existing prompt test file if present, otherwise create `tests/test_prompt.py`

- [ ] **Step 1: Inspect current prompt function**

Run:

```powershell
Get-Content -Raw -Encoding UTF8 src\qq_ai_bot\llm\prompt.py
```

Expected: identify the current `build_prompt(...)` signature before editing.

- [ ] **Step 2: Write failing prompt test**

If `tests/test_prompt.py` does not exist, create it:

```python
from qq_ai_bot.llm.prompt import build_prompt
from qq_ai_bot.memory.context import ChatMessage


def test_build_prompt_includes_search_results_when_present():
    messages = build_prompt(
        recent_context=[
            ChatMessage(user_id=1, nickname="alice", content="刚才聊模型更新"),
        ],
        current_message="帮我查一下今天豆包有什么更新",
        current_nickname="alice",
        search_context=[
            "来源 1: 火山方舟文档 - 豆包模型能力更新摘要 https://example.com/doubao",
        ],
    )

    joined = "\n".join(message["content"] for message in messages)
    assert "联网搜索资料" in joined
    assert "来源 1" in joined
    assert "https://example.com/doubao" in joined
```

- [ ] **Step 3: Run prompt test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_prompt.py -v
```

Expected: fails because `build_prompt()` does not accept `search_context`.

- [ ] **Step 4: Modify prompt builder**

Update `src/qq_ai_bot/llm/prompt.py` so the function accepts `search_context`:

```python
def build_prompt(
    *,
    recent_context: list[ChatMessage],
    current_message: str,
    current_nickname: str,
    search_context: list[str] | None = None,
) -> list[dict[str, str]]:
```

Inside the system or context message construction, add:

```python
    search_block = ""
    if search_context:
        search_block = "\n\n联网搜索资料：\n" + "\n".join(search_context)
```

Append `search_block` to the context content that is sent before the current user message. The final prompt must tell the model:

```text
如果使用联网搜索资料回答，请简短说明信息来自搜索摘要；不要大段复制来源原文；不确定的信息要说明不确定。
```

- [ ] **Step 5: Run prompt tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_prompt.py -v
```

Expected: prompt tests pass.

- [ ] **Step 6: Commit**

```powershell
git add src\qq_ai_bot\llm\prompt.py tests\test_prompt.py
git commit -m "feat: add search context to llm prompt"
```

### Task 7: Message Loop Integration

**Files:**
- Modify: `src/qq_ai_bot/services/message_loop.py`
- Modify: `tests/test_message_loop.py`

- [ ] **Step 1: Add integration test helpers**

Add to `tests/test_message_loop.py` if equivalent helpers do not already exist:

```python
from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.tools.web_search import SearchResult


class FakeSearchClient:
    def __init__(self):
        self.queries = []

    async def search(self, query: str, *, max_results: int):
        self.queries.append((query, max_results))
        return [
            SearchResult(
                title="豆包更新",
                url="https://example.com/doubao",
                snippet="今天发布了模型能力说明。",
            )
        ]
```

- [ ] **Step 2: Write failing tests for safety and search**

Add to `tests/test_message_loop.py`:

```python
async def test_privacy_request_replies_without_llm_or_memory(group_event):
    actions = FakeActions()
    llm = FakeLLM("should not be used")

    handled = await handle_group_message(
        group_event(message="[CQ:at,qq=200] 帮我查一下张三手机号", group_id=100, user_id=1),
        target_group_id=100,
        bot_qq=200,
        actions=actions,
        llm=llm,
        memory=GroupMemory(max_messages=10),
    )

    assert handled is True
    assert "隐私" in actions.sent_messages[0][1]
    assert llm.calls == []


async def test_search_context_is_added_when_enabled_and_budget_allows(group_event):
    actions = FakeActions()
    llm = FakeLLM("搜索后的回答")
    search = FakeSearchClient()

    handled = await handle_group_message(
        group_event(message="[CQ:at,qq=200] 帮我搜一下今天豆包更新", group_id=100, user_id=1),
        target_group_id=100,
        bot_qq=200,
        actions=actions,
        llm=llm,
        memory=GroupMemory(max_messages=10),
        enable_web_search=True,
        search_budget=DailyUsageBudget(group_daily_limit=20, user_daily_limit=5),
        web_search=search,
        search_max_results=3,
    )

    assert handled is True
    assert search.queries == [("[CQ:at,qq=200] 帮我搜一下今天豆包更新", 3)]
    prompt_text = "\n".join(message["content"] for message in llm.calls[0])
    assert "联网搜索资料" in prompt_text
    assert "https://example.com/doubao" in prompt_text


async def test_search_request_continues_without_search_when_disabled(group_event):
    actions = FakeActions()
    llm = FakeLLM("普通回答")
    search = FakeSearchClient()

    handled = await handle_group_message(
        group_event(message="[CQ:at,qq=200] 帮我搜一下今天豆包更新", group_id=100, user_id=1),
        target_group_id=100,
        bot_qq=200,
        actions=actions,
        llm=llm,
        memory=GroupMemory(max_messages=10),
        enable_web_search=False,
        search_budget=DailyUsageBudget(group_daily_limit=20, user_daily_limit=5),
        web_search=search,
    )

    assert handled is True
    assert search.queries == []
    assert actions.sent_messages[0][1] == "普通回答"
```

Adapt helper names to the existing `tests/test_message_loop.py` fixtures. Do not change asserted behavior.

- [ ] **Step 3: Run integration tests to verify they fail**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_message_loop.py -v
```

Expected: fails because `handle_group_message()` does not accept search arguments and does not call safety policy.

- [ ] **Step 4: Extend message loop signature**

Update `src/qq_ai_bot/services/message_loop.py` imports:

```python
from datetime import date

from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.policy.safety import SafetyAction, classify_message_safety
from qq_ai_bot.policy.tool_trigger import detect_search_trigger
from qq_ai_bot.tools.web_search import SearchDisabledError, WebSearchClient
```

Update `handle_group_message(...)` parameters:

```python
    enable_web_search: bool = False,
    search_budget: DailyUsageBudget | None = None,
    web_search: WebSearchClient | None = None,
    search_max_results: int = 3,
) -> bool:
```

- [ ] **Step 5: Add safety gate before memory write**

In `handle_group_message(...)`, after ping handling and before `memory.add_message(...)`, add:

```python
    safety = classify_message_safety(message_text)
    if safety.action in {SafetyAction.DEESCALATE, SafetyAction.REFUSE} and is_at_bot(event.message, bot_qq=bot_qq):
        if safety.reply:
            await actions.send_group_message(event.group_id, safety.reply)
        return True
```

This prevents rejected privacy/high-risk prompts from entering chat memory.

- [ ] **Step 6: Add search context construction before prompt build**

Inside the `if llm is not None and memory is not None and is_at_bot(...)` block, before `build_prompt(...)`, add:

```python
        search_context: list[str] = []
        search_trigger = detect_search_trigger(message_text)
        if (
            enable_web_search
            and search_trigger.should_search
            and search_trigger.query
            and web_search is not None
            and search_budget is not None
            and search_budget.try_consume(group_id=event.group_id, user_id=event.user_id, day=date.today())
        ):
            try:
                results = await web_search.search(search_trigger.query, max_results=search_max_results)
            except SearchDisabledError:
                logger.info("Web search disabled for group %s", event.group_id)
            except Exception:
                logger.exception("Web search failed for group %s", event.group_id)
            else:
                search_context = [
                    f"来源 {index}: {result.title} - {result.snippet} {result.url}"
                    for index, result in enumerate(results, start=1)
                ]
```

Update `build_prompt(...)` call:

```python
        messages = build_prompt(
            recent_context=recent[:-1],
            current_message=message_text,
            current_nickname=event.nickname,
            search_context=search_context,
        )
```

- [ ] **Step 7: Run message loop tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_message_loop.py -v
```

Expected: all message loop tests pass.

- [ ] **Step 8: Run related policy tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_safety_policy.py tests\test_tool_trigger.py tests\test_usage_budget.py tests\test_web_search_tool.py tests\test_message_loop.py -v
```

Expected: all selected tests pass.

- [ ] **Step 9: Commit**

```powershell
git add src\qq_ai_bot\services\message_loop.py tests\test_message_loop.py
git commit -m "feat: gate llm replies with safety and search policy"
```

### Task 8: Application Wiring

**Files:**
- Modify: `src/qq_ai_bot/main.py`
- Modify: `tests/test_main.py`

- [ ] **Step 1: Add failing main wiring test**

Add to `tests/test_main.py`:

```python
from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.tools.web_search import DisabledWebSearchClient


def test_build_advanced_dependencies_uses_settings():
    settings = Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        target_group_id=100,
        bot_qq=200,
        enable_web_search=True,
        daily_search_limit_per_group=7,
        daily_search_limit_per_user=2,
        search_max_results=1,
    )

    deps = build_advanced_dependencies(settings)

    assert deps["enable_web_search"] is True
    assert isinstance(deps["search_budget"], DailyUsageBudget)
    assert isinstance(deps["web_search"], DisabledWebSearchClient)
    assert deps["search_max_results"] == 1
```

- [ ] **Step 2: Run main test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_main.py -v
```

Expected: fails because `build_advanced_dependencies` does not exist.

- [ ] **Step 3: Implement dependency builder**

Update `src/qq_ai_bot/main.py` imports:

```python
from qq_ai_bot.budget.usage import DailyUsageBudget
from qq_ai_bot.tools.web_search import DisabledWebSearchClient
```

Add:

```python
def build_advanced_dependencies(settings: Settings) -> dict[str, object]:
    return {
        "enable_web_search": settings.enable_web_search,
        "search_budget": DailyUsageBudget(
            group_daily_limit=settings.daily_search_limit_per_group,
            user_daily_limit=settings.daily_search_limit_per_user,
        ),
        "web_search": DisabledWebSearchClient(),
        "search_max_results": settings.search_max_results,
    }
```

Where `handle_group_message(...)` is called, unpack these dependencies:

```python
    advanced_dependencies = build_advanced_dependencies(settings)
```

and pass:

```python
                    enable_web_search=advanced_dependencies["enable_web_search"],
                    search_budget=advanced_dependencies["search_budget"],
                    web_search=advanced_dependencies["web_search"],
                    search_max_results=advanced_dependencies["search_max_results"],
```

- [ ] **Step 4: Run main tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests\test_main.py -v
```

Expected: all main tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src\qq_ai_bot\main.py tests\test_main.py
git commit -m "feat: wire advanced capability dependencies"
```

### Task 9: Docs and Runbook Update

**Files:**
- Modify: `README.md`
- Create: `docs/m2-5-local-runbook.md`
- Modify: `docs/roadmap.md`

- [ ] **Step 1: Update README advanced capability section**

Add a concise section to `README.md`:

```markdown
## M2.5 能力状态

当前默认文本模型仍是火山方舟 `doubao-seed-2.0-lite`。

M2.5 增加的是策略层和接口层：

- 安全分级：正常问题继续回答；隐私、高风险和骂战请求会被拦截或降温。
- 搜索触发：识别“搜一下、查一下、最新、今天、现在”等请求。
- 成本控制：搜索按群和用户做每日次数限制。
- 搜索工具：默认关闭，当前使用禁用态客户端，不会真实联网或产生搜索费用。

真实联网搜索供应商需要在确认官方能力、价格和稳定性后接入。
```

- [ ] **Step 2: Add M2.5 local runbook**

Create `docs/m2-5-local-runbook.md`:

```markdown
# M2.5 本地运行手册

## 当前范围

M2.5 只上线搜索、安全和成本控制的基础框架：

- 安全策略会拦截隐私、高风险和骂战请求。
- 搜索触发策略会识别需要联网的问题。
- 搜索预算会限制每日搜索次数。
- 搜索客户端默认是禁用态，不会真实联网。

## 环境变量

```env
ENABLE_WEB_SEARCH=false
DAILY_SEARCH_LIMIT_PER_GROUP=20
DAILY_SEARCH_LIMIT_PER_USER=5
SEARCH_MAX_RESULTS=3
```

默认模型保持：

```env
LLM_BASE_URL=https://ark.cn-beijing.volces.com/api/v3
LLM_MODEL=doubao-seed-2.0-lite
```

## 本地验证

安装：

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

测试：

```powershell
.\.venv\Scripts\python.exe -m pytest
```

## 群内验证

可验证的输入：

- `@机器人 Python list 和 tuple 有什么区别`
- `@机器人 帮我查一下张三手机号`
- `@机器人 帮我骂一下这个人`
- `@机器人 帮我搜一下今天豆包有什么更新`

预期：

- 正常问题走 LLM。
- 隐私请求直接拒绝并给替代方向。
- 骂战请求降温。
- 搜索请求在默认关闭时仍走普通 LLM，不产生真实搜索请求。
```

- [ ] **Step 3: Update roadmap status**

In `docs/roadmap.md`, mark M2.5 as current implementation stage:

```markdown
### M2.5：搜索、安全和成本策略

状态：计划完成，准备实现。
```

After implementation, update to:

```markdown
状态：基础策略层完成，真实搜索供应商待选型接入。
```

- [ ] **Step 4: Commit**

```powershell
git add README.md docs\m2-5-local-runbook.md docs\roadmap.md
git commit -m "docs: document m2.5 local behavior"
```

### Task 10: Final Verification

**Files:**
- All files touched by Tasks 1-9

- [ ] **Step 1: Run full test suite**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 2: Scan for wrong default model**

Run:

```powershell
rg "gp[t]-4|OPENAI_API_KE[Y]|LLM_MODEL=.*gp[t]|doubao-seed-2.0(?!-lite)" README.md docs .env.example src tests
```

Expected: no default-model regressions. OpenAI may appear only in docs as protocol/reference text, not as default configuration.

- [ ] **Step 3: Scan for plan/doc placeholders**

Run:

```powershell
rg "TB[D]|TO[D]O|implement late[r]|fill in detail[s]|Similar to Tas[k]|add appropriat[e]|Write tests for the abov[e]" README.md docs src tests
```

Expected: no placeholder text introduced by this implementation.

- [ ] **Step 4: Inspect git diff**

Run:

```powershell
git status --short
git diff -- README.md .env.example docs src tests
```

Expected: only M2.5 safety/search/budget files and docs are changed.

- [ ] **Step 5: Final commit if any verification-only docs changed**

```powershell
git add README.md .env.example docs src tests
git commit -m "chore: finalize m2.5 search safety budget"
```

Skip this commit if there are no uncommitted changes after Task 9.

## Self-Review

- Spec coverage:
  - Web search: covered by trigger policy, disabled tool interface, config, budget, prompt search context, and docs.
  - Chat memory and summaries: intentionally not implemented in M2.5; preserved for M4 because SQLite persistence is needed first.
  - User feature memory: intentionally not implemented in M2.5; preserved for M4 with explicit privacy constraints.
  - Safety: covered by deterministic classifier and message loop gate.
  - Image input/output: intentionally not implemented in M2.5; remains M5.
  - Voice transcription: intentionally not implemented in M2.5; remains M6 optional.
  - Model and price: default text model remains `doubao-seed-2.0-lite`; real paid providers are not connected in M2.5.
- Placeholder scan targets are listed in Task 10.
- Type consistency:
  - `SafetyAction`, `SafetyDecision`, `SearchTrigger`, `DailyUsageBudget`, `SearchResult`, `WebSearchClient`, `DisabledWebSearchClient`, and `SearchDisabledError` are defined before integration tasks use them.
  - `build_prompt(..., search_context=None)` remains backward compatible with current callers.
  - `handle_group_message(...)` advanced arguments have defaults, so existing tests and callers continue to work.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-06-13-m2-5-search-safety-budget.md`. Two execution options:

1. Subagent-Driven (recommended) - dispatch a fresh subagent per task, review between tasks, fast iteration.
2. Inline Execution - execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?
