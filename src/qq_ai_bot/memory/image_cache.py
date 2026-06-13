from __future__ import annotations

from dataclasses import dataclass

from qq_ai_bot.onebot.events import ImageAttachment


@dataclass(frozen=True)
class CachedImages:
    group_id: int
    user_id: int
    images: list[ImageAttachment]


class RecentImageCache:
    def __init__(self, *, max_entries: int = 50) -> None:
        self._max_entries = max_entries
        self._entries: list[CachedImages] = []

    def remember(
        self,
        *,
        group_id: int,
        user_id: int,
        images: list[ImageAttachment],
    ) -> None:
        if not images:
            return
        self._entries.append(
            CachedImages(group_id=group_id, user_id=user_id, images=list(images))
        )
        if len(self._entries) > self._max_entries:
            self._entries = self._entries[-self._max_entries :]

    def get_latest(self, *, group_id: int, user_id: int) -> list[ImageAttachment]:
        for entry in reversed(self._entries):
            if entry.group_id == group_id and entry.user_id == user_id:
                return list(entry.images)
        return []
