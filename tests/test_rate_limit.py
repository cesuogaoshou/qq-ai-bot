from datetime import datetime, timedelta, timezone

from qq_ai_bot.policy.rate_limit import CooldownLimiter


def test_first_request_is_allowed() -> None:
    limiter = CooldownLimiter(group_cooldown_seconds=20, user_cooldown_seconds=10)

    assert limiter.try_consume(
        group_id=100,
        user_id=1,
        now=datetime(2026, 6, 13, tzinfo=timezone.utc),
    ) is True


def test_group_cooldown_blocks_second_group_request() -> None:
    limiter = CooldownLimiter(group_cooldown_seconds=20, user_cooldown_seconds=0)
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)

    assert limiter.try_consume(group_id=100, user_id=1, now=now) is True
    assert limiter.try_consume(
        group_id=100,
        user_id=2,
        now=now + timedelta(seconds=5),
    ) is False


def test_user_cooldown_blocks_same_user_after_group_window() -> None:
    limiter = CooldownLimiter(group_cooldown_seconds=0, user_cooldown_seconds=10)
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)

    assert limiter.try_consume(group_id=100, user_id=1, now=now) is True
    assert limiter.try_consume(
        group_id=100,
        user_id=1,
        now=now + timedelta(seconds=5),
    ) is False


def test_next_window_is_allowed() -> None:
    limiter = CooldownLimiter(group_cooldown_seconds=20, user_cooldown_seconds=10)
    now = datetime(2026, 6, 13, tzinfo=timezone.utc)

    assert limiter.try_consume(group_id=100, user_id=1, now=now) is True
    assert limiter.try_consume(
        group_id=100,
        user_id=1,
        now=now + timedelta(seconds=21),
    ) is True
