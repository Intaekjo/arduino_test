from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class LinkPhase(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAULT = "fault"


@dataclass(slots=True)
class SessionState:
    phase: LinkPhase = LinkPhase.DISCONNECTED
    active_port: str | None = None
    firmware_version: str = "-"
    controls_enabled: bool = False
    parser_errors: int = 0
    last_error: str = ""

    def begin_connect(self, port: str) -> None:
        self.phase = LinkPhase.CONNECTING
        self.active_port = port
        self.firmware_version = "-"
        self.controls_enabled = False
        self.parser_errors = 0
        self.last_error = ""

    def mark_ready(self, firmware_version: str) -> None:
        self.phase = LinkPhase.CONNECTED
        self.firmware_version = firmware_version
        self.controls_enabled = True
        self.last_error = ""

    def mark_disconnect(self) -> None:
        self.phase = LinkPhase.DISCONNECTED
        self.controls_enabled = False
        self.active_port = None
        self.last_error = ""

    def mark_fault(self, message: str) -> None:
        self.phase = LinkPhase.FAULT
        self.controls_enabled = False
        self.last_error = message

    def register_parse_error(self, limit: int) -> bool:
        self.parser_errors += 1
        if self.parser_errors >= limit:
            self.controls_enabled = False
            self.last_error = "Protocol parsing lockout"
            return True
        return False

