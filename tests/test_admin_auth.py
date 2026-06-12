from qq_ai_bot.admin.auth import is_admin


def test_configured_admin_is_allowed() -> None:
    assert is_admin(user_id=123, admin_ids={123, 456}) is True


def test_non_admin_is_denied() -> None:
    assert is_admin(user_id=789, admin_ids={123, 456}) is False


def test_empty_admin_list_denies_everyone() -> None:
    assert is_admin(user_id=123, admin_ids=set()) is False
