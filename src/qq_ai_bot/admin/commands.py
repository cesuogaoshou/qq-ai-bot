from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class AdminCommandType(StrEnum):
    ON = "on"
    OFF = "off"
    STATUS = "status"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class AdminCommand:
    type: AdminCommandType


def parse_admin_command(message: str) -> AdminCommand | None:
    text = message.strip()
    if not text.startswith("/bot"):
        return None
    parts = text.split()
    if len(parts) != 2:
        return AdminCommand(AdminCommandType.UNKNOWN)
    command = parts[1].lower()
    if command == "on":
        return AdminCommand(AdminCommandType.ON)
    if command == "off":
        return AdminCommand(AdminCommandType.OFF)
    if command == "status":
        return AdminCommand(AdminCommandType.STATUS)
    return AdminCommand(AdminCommandType.UNKNOWN)
