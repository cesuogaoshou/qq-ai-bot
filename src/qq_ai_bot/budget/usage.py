from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date


@dataclass
class DailyUsageBudget:
    group_daily_limit: int
    user_daily_limit: int
    _group_counts: dict[tuple[date, int], int] = field(
        default_factory=lambda: defaultdict(int)
    )
    _user_counts: dict[tuple[date, int, int], int] = field(
        default_factory=lambda: defaultdict(int)
    )

    def try_consume(self, *, group_id: int, user_id: int, day: date) -> bool:
        group_key = (day, group_id)
        user_key = (day, group_id, user_id)
        if self.group_daily_limit <= 0 or self.user_daily_limit <= 0:
            return False
        if self._group_counts[group_key] >= self.group_daily_limit:
            return False
        if self._user_counts[user_key] >= self.user_daily_limit:
            return False
        self._group_counts[group_key] += 1
        self._user_counts[user_key] += 1
        return True
