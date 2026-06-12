from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class CooldownLimiter:
    group_cooldown_seconds: int
    user_cooldown_seconds: int
    _last_group_at: dict[int, datetime] = field(default_factory=dict)
    _last_user_at: dict[tuple[int, int], datetime] = field(default_factory=dict)

    def try_consume(self, *, group_id: int, user_id: int, now: datetime) -> bool:
        group_last = self._last_group_at.get(group_id)
        if group_last is not None and not _window_elapsed(
            group_last,
            now,
            self.group_cooldown_seconds,
        ):
            return False

        user_key = (group_id, user_id)
        user_last = self._last_user_at.get(user_key)
        if user_last is not None and not _window_elapsed(
            user_last,
            now,
            self.user_cooldown_seconds,
        ):
            return False

        self._last_group_at[group_id] = now
        self._last_user_at[user_key] = now
        return True


def _window_elapsed(last_seen: datetime, now: datetime, seconds: int) -> bool:
    if seconds <= 0:
        return True
    return now - last_seen >= timedelta(seconds=seconds)
