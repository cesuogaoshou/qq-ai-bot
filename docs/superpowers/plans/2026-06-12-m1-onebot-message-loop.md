# M1 OneBot Message Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the M1 local message loop: load config, parse OneBot group messages, ignore non-target groups, and send a fixed reply for a test command.

**Architecture:** Keep protocol details inside `qq_ai_bot.onebot`, configuration in `qq_ai_bot.config`, and orchestration in `qq_ai_bot.services`. M1 does not call an LLM, does not persist SQLite data, and does not implement admin state; it only proves the OneBot receive/send loop.

**Tech Stack:** Python 3.12+, pydantic, httpx, websockets, pytest.

---

## File Structure

Create and modify these files:

- `src/qq_ai_bot/config.py`: typed settings loaded from environment variables.
- `src/qq_ai_bot/onebot/events.py`: minimal OneBot group-message event model and parser.
- `src/qq_ai_bot/onebot/actions.py`: OneBot HTTP action client for `send_group_msg`.
- `src/qq_ai_bot/onebot/client.py`: WebSocket event stream wrapper.
- `src/qq_ai_bot/services/message_loop.py`: M1 orchestration; target group filter and fixed reply trigger.
- `src/qq_ai_bot/main.py`: CLI entry point for running the bot.
- `tests/test_config.py`: config loading tests.
- `tests/test_onebot_events.py`: event parsing tests.
- `tests/test_onebot_actions.py`: action client tests using a fake transport.
- `tests/test_message_loop.py`: service behavior tests using fake event/action clients.
- `README.md`: add M1 local run command.

## M1 Behavior

M1 fixed trigger:

```text
/bot ping
```

Expected reply:

```text
pong
```

M1 accepts only messages from `TARGET_GROUP_ID`. Messages from other groups are ignored. Non-group events are ignored. Group messages that do not equal `/bot ping` after trimming whitespace are ignored.

## Task 1: Config Loader

**Files:**
- Create: `src/qq_ai_bot/config.py`
- Test: `tests/test_config.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from qq_ai_bot.config import Settings, load_settings


def test_load_settings_reads_required_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.setenv("ONEBOT_ACCESS_TOKEN", "token")
    monkeypatch.setenv("TARGET_GROUP_ID", "123456")

    settings = load_settings()

    assert settings == Settings(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        onebot_access_token="token",
        target_group_id=123456,
    )


def test_load_settings_rejects_missing_target_group(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001")
    monkeypatch.setenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000")
    monkeypatch.delenv("TARGET_GROUP_ID", raising=False)

    with pytest.raises(ValueError, match="TARGET_GROUP_ID"):
        load_settings()
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -q
```

Expected: FAIL with `ModuleNotFoundError` or missing `load_settings`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import os

from pydantic import BaseModel


class Settings(BaseModel):
    onebot_ws_url: str
    onebot_http_url: str
    onebot_access_token: str = ""
    target_group_id: int


def load_settings() -> Settings:
    target_group_id = os.getenv("TARGET_GROUP_ID")
    if not target_group_id:
        raise ValueError("TARGET_GROUP_ID is required")

    return Settings(
        onebot_ws_url=os.getenv("ONEBOT_WS_URL", "ws://127.0.0.1:3001"),
        onebot_http_url=os.getenv("ONEBOT_HTTP_URL", "http://127.0.0.1:3000"),
        onebot_access_token=os.getenv("ONEBOT_ACCESS_TOKEN", ""),
        target_group_id=int(target_group_id),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_config.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/qq_ai_bot/config.py tests/test_config.py
git commit -m "feat: add runtime settings loader"
git push
```

## Task 2: OneBot Event Parsing

**Files:**
- Create: `src/qq_ai_bot/onebot/__init__.py`
- Create: `src/qq_ai_bot/onebot/events.py`
- Test: `tests/test_onebot_events.py`

- [ ] **Step 1: Write the failing test**

```python
from qq_ai_bot.onebot.events import GroupMessageEvent, parse_group_message


def test_parse_group_message_from_onebot_payload() -> None:
    payload = {
        "post_type": "message",
        "message_type": "group",
        "group_id": 123456,
        "user_id": 42,
        "message": "/bot ping",
        "sender": {"nickname": "Alice"},
        "message_id": 1001,
        "time": 1710000000,
    }

    event = parse_group_message(payload)

    assert event == GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="/bot ping",
        nickname="Alice",
        message_id=1001,
        time=1710000000,
    )


def test_parse_group_message_returns_none_for_non_group_event() -> None:
    payload = {
        "post_type": "message",
        "message_type": "private",
        "user_id": 42,
        "message": "/bot ping",
    }

    assert parse_group_message(payload) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_onebot_events.py -q
```

Expected: FAIL with `ModuleNotFoundError` or missing `parse_group_message`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class GroupMessageEvent(BaseModel):
    group_id: int
    user_id: int
    message: str
    nickname: str = ""
    message_id: int | None = None
    time: int | None = None


def parse_group_message(payload: dict[str, Any]) -> GroupMessageEvent | None:
    if payload.get("post_type") != "message":
        return None
    if payload.get("message_type") != "group":
        return None

    sender = payload.get("sender") or {}
    return GroupMessageEvent(
        group_id=int(payload["group_id"]),
        user_id=int(payload["user_id"]),
        message=str(payload.get("message", "")),
        nickname=str(sender.get("nickname", "")),
        message_id=payload.get("message_id"),
        time=payload.get("time"),
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_onebot_events.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/qq_ai_bot/onebot tests/test_onebot_events.py
git commit -m "feat: parse onebot group message events"
git push
```

## Task 3: OneBot Action Client

**Files:**
- Create: `src/qq_ai_bot/onebot/actions.py`
- Test: `tests/test_onebot_actions.py`

- [ ] **Step 1: Write the failing test**

```python
import httpx
import pytest

from qq_ai_bot.onebot.actions import OneBotActionClient


@pytest.mark.anyio
async def test_send_group_message_posts_onebot_action() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"status": "ok", "retcode": 0, "data": {}})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport, base_url="http://onebot.test") as http:
        client = OneBotActionClient(http=http, access_token="secret")
        await client.send_group_message(group_id=123456, message="pong")

    assert len(requests) == 1
    assert requests[0].url.path == "/send_group_msg"
    assert requests[0].headers["Authorization"] == "Bearer secret"
    assert requests[0].read() == b'{"group_id":123456,"message":"pong"}'
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_onebot_actions.py -q
```

Expected: FAIL with missing `OneBotActionClient`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import httpx


class OneBotActionClient:
    def __init__(self, http: httpx.AsyncClient, access_token: str = "") -> None:
        self._http = http
        self._access_token = access_token

    async def send_group_message(self, group_id: int, message: str) -> None:
        headers = {}
        if self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"

        response = await self._http.post(
            "/send_group_msg",
            json={"group_id": group_id, "message": message},
            headers=headers,
        )
        response.raise_for_status()
        data = response.json()
        if data.get("retcode") != 0:
            raise RuntimeError(f"OneBot send_group_msg failed: {data}")
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_onebot_actions.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/qq_ai_bot/onebot/actions.py tests/test_onebot_actions.py
git commit -m "feat: add onebot group message action client"
git push
```

## Task 4: Message Loop Service

**Files:**
- Create: `src/qq_ai_bot/services/__init__.py`
- Create: `src/qq_ai_bot/services/message_loop.py`
- Test: `tests/test_message_loop.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from qq_ai_bot.onebot.events import GroupMessageEvent
from qq_ai_bot.services.message_loop import handle_group_message


class FakeActions:
    def __init__(self) -> None:
        self.sent: list[tuple[int, str]] = []

    async def send_group_message(self, group_id: int, message: str) -> None:
        self.sent.append((group_id, message))


@pytest.mark.anyio
async def test_handle_group_message_replies_to_ping_in_target_group() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message=" /bot ping ",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        actions=actions,
    )

    assert handled is True
    assert actions.sent == [(123456, "pong")]


@pytest.mark.anyio
async def test_handle_group_message_ignores_other_groups() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=999999,
        user_id=42,
        message="/bot ping",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        actions=actions,
    )

    assert handled is False
    assert actions.sent == []


@pytest.mark.anyio
async def test_handle_group_message_ignores_non_ping_messages() -> None:
    actions = FakeActions()
    event = GroupMessageEvent(
        group_id=123456,
        user_id=42,
        message="hello",
        nickname="Alice",
    )

    handled = await handle_group_message(
        event,
        target_group_id=123456,
        actions=actions,
    )

    assert handled is False
    assert actions.sent == []
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_message_loop.py -q
```

Expected: FAIL with missing `handle_group_message`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

from typing import Protocol

from qq_ai_bot.onebot.events import GroupMessageEvent


class GroupMessageActions(Protocol):
    async def send_group_message(self, group_id: int, message: str) -> None:
        ...


async def handle_group_message(
    event: GroupMessageEvent,
    *,
    target_group_id: int,
    actions: GroupMessageActions,
) -> bool:
    if event.group_id != target_group_id:
        return False
    if event.message.strip() != "/bot ping":
        return False

    await actions.send_group_message(event.group_id, "pong")
    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_message_loop.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/qq_ai_bot/services tests/test_message_loop.py
git commit -m "feat: add m1 ping message loop"
git push
```

## Task 5: WebSocket Event Client

**Files:**
- Create: `src/qq_ai_bot/onebot/client.py`
- Test: `tests/test_onebot_client.py`

- [ ] **Step 1: Write the failing test**

```python
import json

import pytest

from qq_ai_bot.onebot.client import iter_group_messages


class FakeWebSocket:
    def __init__(self, payloads: list[dict]) -> None:
        self._messages = [json.dumps(payload) for payload in payloads]

    def __aiter__(self):
        return self

    async def __anext__(self) -> str:
        if not self._messages:
            raise StopAsyncIteration
        return self._messages.pop(0)


@pytest.mark.anyio
async def test_iter_group_messages_yields_only_group_messages() -> None:
    websocket = FakeWebSocket(
        [
            {
                "post_type": "message",
                "message_type": "private",
                "user_id": 1,
                "message": "ignored",
            },
            {
                "post_type": "message",
                "message_type": "group",
                "group_id": 123456,
                "user_id": 42,
                "message": "/bot ping",
                "sender": {"nickname": "Alice"},
            },
        ]
    )

    events = [event async for event in iter_group_messages(websocket)]

    assert len(events) == 1
    assert events[0].group_id == 123456
    assert events[0].message == "/bot ping"
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_onebot_client.py -q
```

Expected: FAIL with missing `iter_group_messages`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from qq_ai_bot.onebot.events import GroupMessageEvent, parse_group_message


async def iter_group_messages(websocket: Any) -> AsyncIterator[GroupMessageEvent]:
    async for raw_message in websocket:
        payload = json.loads(raw_message)
        event = parse_group_message(payload)
        if event is not None:
            yield event
```

- [ ] **Step 4: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_onebot_client.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/qq_ai_bot/onebot/client.py tests/test_onebot_client.py
git commit -m "feat: add onebot websocket event iterator"
git push
```

## Task 6: Runtime Entry Point

**Files:**
- Create: `src/qq_ai_bot/main.py`
- Modify: `pyproject.toml`
- Modify: `README.md`
- Test: `tests/test_main.py`

- [ ] **Step 1: Write the failing test**

```python
import pytest

from qq_ai_bot.main import build_startup_summary


def test_build_startup_summary_hides_access_token() -> None:
    summary = build_startup_summary(
        onebot_ws_url="ws://127.0.0.1:3001",
        onebot_http_url="http://127.0.0.1:3000",
        access_token="secret",
        target_group_id=123456,
    )

    assert "ws://127.0.0.1:3001" in summary
    assert "http://127.0.0.1:3000" in summary
    assert "123456" in summary
    assert "secret" not in summary
    assert "access_token=set" in summary
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_main.py -q
```

Expected: FAIL with missing `build_startup_summary`.

- [ ] **Step 3: Write minimal implementation**

```python
from __future__ import annotations

import asyncio
import logging

import httpx
import websockets

from qq_ai_bot.config import load_settings
from qq_ai_bot.onebot.actions import OneBotActionClient
from qq_ai_bot.onebot.client import iter_group_messages
from qq_ai_bot.services.message_loop import handle_group_message


logger = logging.getLogger(__name__)


def build_startup_summary(
    *,
    onebot_ws_url: str,
    onebot_http_url: str,
    access_token: str,
    target_group_id: int,
) -> str:
    token_state = "set" if access_token else "empty"
    return (
        f"onebot_ws_url={onebot_ws_url} "
        f"onebot_http_url={onebot_http_url} "
        f"target_group_id={target_group_id} "
        f"access_token={token_state}"
    )


async def run() -> None:
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    logger.info(
        "Starting QQ AI bot: %s",
        build_startup_summary(
            onebot_ws_url=settings.onebot_ws_url,
            onebot_http_url=settings.onebot_http_url,
            access_token=settings.onebot_access_token,
            target_group_id=settings.target_group_id,
        ),
    )

    async with httpx.AsyncClient(base_url=settings.onebot_http_url, timeout=10) as http:
        actions = OneBotActionClient(
            http=http,
            access_token=settings.onebot_access_token,
        )
        async with websockets.connect(settings.onebot_ws_url) as websocket:
            async for event in iter_group_messages(websocket):
                handled = await handle_group_message(
                    event,
                    target_group_id=settings.target_group_id,
                    actions=actions,
                )
                if handled:
                    logger.info("Handled /bot ping in group %s", event.group_id)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Add console script to pyproject**

Add this section to `pyproject.toml`:

```toml
[project.scripts]
qq-ai-bot = "qq_ai_bot.main:main"
```

- [ ] **Step 5: Add README M1 run instructions**

Add this to `README.md` under local development:

````markdown
M1 本地消息闭环运行：

```powershell
$env:ONEBOT_WS_URL="ws://127.0.0.1:3001"
$env:ONEBOT_HTTP_URL="http://127.0.0.1:3000"
$env:TARGET_GROUP_ID="你的测试群号"
.\.venv\Scripts\qq-ai-bot.exe
```

在目标群发送 `/bot ping`，预期机器人回复 `pong`。
````

- [ ] **Step 6: Run test to verify it passes**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_main.py -q
```

Expected: PASS.

- [ ] **Step 7: Run all tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 8: Commit**

```powershell
git add src/qq_ai_bot/main.py pyproject.toml README.md tests/test_main.py
git commit -m "feat: add m1 runtime entry point"
git push
```

## Task 7: Final M1 Verification

**Files:**
- Modify only if verification reveals a defect.

- [ ] **Step 1: Reinstall editable package**

Run:

```powershell
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Expected: install succeeds.

- [ ] **Step 2: Run all tests**

Run:

```powershell
.\.venv\Scripts\python.exe -m pytest
```

Expected: all tests pass.

- [ ] **Step 3: Check CLI imports**

Run:

```powershell
.\.venv\Scripts\python.exe -c "from qq_ai_bot.main import main; print(callable(main))"
```

Expected: prints `True`.

- [ ] **Step 4: Review Git status**

Run:

```powershell
git status --short
```

Expected: only intended M1 changes are present before final commit, or clean after commits.

## Self-Review

Spec coverage:

- M1 can connect to OneBot: covered by Task 6 runtime entry point.
- M1 can receive target group messages: covered by Tasks 2, 5, and 6.
- M1 can send a fixed reply: covered by Tasks 3 and 4.
- M1 ignores non-target groups: covered by Task 4.
- M1 logs startup and handled ping events: covered by Task 6.

Scope boundaries:

- No LLM call is included.
- No SQLite persistence is included.
- No admin state is included.
- No multi-group configuration is included beyond `target_group_id`.

Placeholder scan:

- No placeholder markers or unspecified implementation steps remain.

Type consistency:

- `target_group_id` is consistently an `int`.
- `GroupMessageEvent` fields are consistently used across event parsing and service tests.
- `send_group_message(group_id: int, message: str)` is the action boundary across fake and real clients.
