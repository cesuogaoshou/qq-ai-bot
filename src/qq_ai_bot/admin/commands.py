from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AdminCommandType(StrEnum):
    ON = "on"
    OFF = "off"
    STATUS = "status"
    SUMMARY_RECENT = "summary_recent"
    SUMMARY_CLEAR = "summary_clear"
    MEMORY_STATUS = "memory_status"
    MEMORY_CLEAR = "memory_clear"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AdminCommand:
    type: AdminCommandType


def parse_admin_command(message: str) -> AdminCommand | None:
    text = message.strip()
    if not text.startswith("/bot"):
        return None
    parts = text.split()
    command = " ".join(part.lower() for part in parts[1:])
    if command == "on":
        return AdminCommand(AdminCommandType.ON)
    if command == "off":
        return AdminCommand(AdminCommandType.OFF)
    if command == "status":
        return AdminCommand(AdminCommandType.STATUS)
    if command == "summary recent":
        return AdminCommand(AdminCommandType.SUMMARY_RECENT)
    if command == "summary clear":
        return AdminCommand(AdminCommandType.SUMMARY_CLEAR)
    if command == "memory status":
        return AdminCommand(AdminCommandType.MEMORY_STATUS)
    if command == "memory clear":
        return AdminCommand(AdminCommandType.MEMORY_CLEAR)
    return AdminCommand(AdminCommandType.UNKNOWN)
