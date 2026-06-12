from __future__ import annotations


class GroupMemory:
    """In-memory ring buffer for recent group messages."""

    def __init__(self, max_messages: int = 30) -> None:
        self._messages: list[dict[str, str]] = []
        self._max_messages = max_messages

    def add_message(self, *, user_id: int, nickname: str, content: str) -> None:
        self._messages.append(
            {"role": "user", "content": f"{nickname}: {content}"}
        )
        if len(self._messages) > self._max_messages:
            self._messages = self._messages[-self._max_messages :]

    def get_recent(self) -> list[dict[str, str]]:
        return list(self._messages)
