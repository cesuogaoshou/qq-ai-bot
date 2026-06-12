from __future__ import annotations

import re

_AT_PATTERN = re.compile(r"\[CQ:at,qq=(\d+)[^\]]*\]")


def parse_at_qqs(message: str) -> list[int]:
    """Extract all @ QQ numbers from a OneBot message."""
    return [int(m) for m in _AT_PATTERN.findall(message)]


def is_at_bot(message: str, *, bot_qq: int) -> bool:
    """Check if the bot was @-mentioned in this message."""
    return bot_qq in parse_at_qqs(message)
