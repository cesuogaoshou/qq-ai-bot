from datetime import date

from qq_ai_bot.budget.usage import DailyUsageBudget


def test_group_limit_allows_until_limit() -> None:
    budget = DailyUsageBudget(group_daily_limit=2, user_daily_limit=5)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=2, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=3, day=date(2026, 6, 13)) is False


def test_user_limit_allows_until_limit() -> None:
    budget = DailyUsageBudget(group_daily_limit=5, user_daily_limit=2)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is False


def test_next_day_resets_limits() -> None:
    budget = DailyUsageBudget(group_daily_limit=1, user_daily_limit=1)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is True
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is False
    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 14)) is True


def test_zero_limit_always_blocks() -> None:
    budget = DailyUsageBudget(group_daily_limit=0, user_daily_limit=5)

    assert budget.try_consume(group_id=100, user_id=1, day=date(2026, 6, 13)) is False
