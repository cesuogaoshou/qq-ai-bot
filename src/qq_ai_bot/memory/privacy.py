from __future__ import annotations

import re


_PHONE_RE = re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)")
_ID_RE = re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)")
_BANK_CARD_RE = re.compile(r"(?<!\d)\d{16,19}(?!\d)")
_ADDRESS_RE = re.compile(r"[\u4e00-\u9fa5]{2,}(?:省|市|区|县)[\u4e00-\u9fa5\d号弄路街道小区室-]{2,}")

_SENSITIVE_INFERENCE_TERMS = (
    "政治倾向",
    "宗教信仰",
    "健康状况",
    "经济状况",
    "感情状况",
    "年龄",
    "性别",
    "私人关系",
)


def redact_sensitive_text(text: str) -> str:
    redacted = _PHONE_RE.sub("[手机号]", text)
    redacted = _ID_RE.sub("[身份证]", redacted)
    redacted = _BANK_CARD_RE.sub("[银行卡]", redacted)
    redacted = _ADDRESS_RE.sub("[住址]", redacted)
    return redacted


def is_sensitive_memory_candidate(text: str) -> bool:
    return any(term in text for term in _SENSITIVE_INFERENCE_TERMS)
