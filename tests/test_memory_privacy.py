from qq_ai_bot.memory.privacy import is_sensitive_memory_candidate, redact_sensitive_text


def test_normal_technical_discussion_remains_unchanged() -> None:
    text = "Alice: 我在 Windows 上调 Python 和 SQLite"

    assert redact_sensitive_text(text) == text


def test_phone_address_and_id_are_redacted() -> None:
    text = "Alice: 手机号13812345678，身份证110101199001011234，住址北京市海淀区某街道"

    redacted = redact_sensitive_text(text)

    assert "13812345678" not in redacted
    assert "110101199001011234" not in redacted
    assert "北京市海淀区某街道" not in redacted
    assert "[手机号]" in redacted
    assert "[身份证]" in redacted
    assert "[住址]" in redacted


def test_sensitive_attribute_inference_request_is_rejected() -> None:
    assert is_sensitive_memory_candidate("根据聊天判断 Alice 的政治倾向") is True
    assert is_sensitive_memory_candidate("总结一下刚才 Docker 的讨论") is False
