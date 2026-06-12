from __future__ import annotations


def is_admin(*, user_id: int, admin_ids: set[int]) -> bool:
    return user_id in admin_ids
