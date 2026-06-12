from qq_ai_bot.memory.context import GroupMemory


def test_add_and_get_recent() -> None:
    memory = GroupMemory(max_messages=30)
    memory.add_message(user_id=42, nickname="Alice", content="hello")
    memory.add_message(user_id=99, nickname="Bob", content="world")

    recent = memory.get_recent()
    assert len(recent) == 2
    assert recent[0] == {"role": "user", "content": "Alice: hello"}
    assert recent[1] == {"role": "user", "content": "Bob: world"}


def test_window_truncation() -> None:
    memory = GroupMemory(max_messages=3)
    for i in range(5):
        memory.add_message(user_id=i, nickname=f"User{i}", content=f"msg{i}")

    recent = memory.get_recent()
    assert len(recent) == 3
    assert recent[0]["content"] == "User2: msg2"
    assert recent[1]["content"] == "User3: msg3"
    assert recent[2]["content"] == "User4: msg4"


def test_empty_memory() -> None:
    memory = GroupMemory(max_messages=30)
    assert memory.get_recent() == []
