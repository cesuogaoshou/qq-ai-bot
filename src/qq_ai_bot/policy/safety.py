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


_PRIVACY_TERMS = ("手机号", "电话号码", "住址", "身份证", "银行卡", "开房", "家庭住址")
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
