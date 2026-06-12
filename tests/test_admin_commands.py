from qq_ai_bot.admin.commands import AdminCommand, AdminCommandType, parse_admin_command


def test_parse_bot_on_command() -> None:
    assert parse_admin_command("  /bot on  ") == AdminCommand(AdminCommandType.ON)


def test_parse_bot_off_command() -> None:
    assert parse_admin_command("/bot off") == AdminCommand(AdminCommandType.OFF)


def test_parse_bot_status_command() -> None:
    assert parse_admin_command("/bot status") == AdminCommand(AdminCommandType.STATUS)


def test_parse_unknown_bot_command() -> None:
    assert parse_admin_command("/bot restart") == AdminCommand(AdminCommandType.UNKNOWN)


def test_non_command_returns_none() -> None:
    assert parse_admin_command("普通聊天") is None


def test_parse_summary_recent_command() -> None:
    assert parse_admin_command("/bot summary recent") == AdminCommand(
        AdminCommandType.SUMMARY_RECENT
    )


def test_parse_summary_clear_command() -> None:
    assert parse_admin_command("/bot summary clear") == AdminCommand(
        AdminCommandType.SUMMARY_CLEAR
    )


def test_parse_memory_status_command() -> None:
    assert parse_admin_command("/bot memory status") == AdminCommand(
        AdminCommandType.MEMORY_STATUS
    )


def test_parse_memory_clear_command() -> None:
    assert parse_admin_command("/bot memory clear") == AdminCommand(
        AdminCommandType.MEMORY_CLEAR
    )
