from __future__ import annotations

import httpx
import pytest

from qq_ai_bot.llm.client import LLMClient


@pytest.mark.anyio
async def test_chat_normal_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={
                "choices": [
                    {"message": {"content": "这是一条测试回复"}}
                ]
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = LLMClient(
            http=http,
            base_url="https://test.api",
            model="test-model",
            api_key="key",
        )
        reply = await client.chat(
            messages=[{"role": "user", "content": "你好"}]
        )

    assert reply == "这是一条测试回复"


@pytest.mark.anyio
async def test_chat_timeout_returns_empty() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = LLMClient(
            http=http,
            base_url="https://test.api",
            model="test-model",
            api_key="key",
        )
        reply = await client.chat(
            messages=[{"role": "user", "content": "你好"}]
        )

    assert reply == ""


@pytest.mark.anyio
async def test_chat_empty_choices_returns_empty() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"choices": []})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = LLMClient(
            http=http,
            base_url="https://test.api",
            model="test-model",
            api_key="key",
        )
        reply = await client.chat(
            messages=[{"role": "user", "content": "你好"}]
        )

    assert reply == ""


@pytest.mark.anyio
async def test_chat_uses_correct_url() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok"}}]},
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http:
        client = LLMClient(
            http=http,
            base_url="https://test.api",
            model="test-model",
            api_key="secret-key",
        )
        await client.chat(
            messages=[{"role": "user", "content": "你好"}]
        )

    assert len(requests) == 1
    assert requests[0].url == "https://test.api/chat/completions"
    assert requests[0].headers["Authorization"] == "Bearer secret-key"
    body = requests[0].read()
    assert b'"model"' in body
    assert b'"test-model"' in body
