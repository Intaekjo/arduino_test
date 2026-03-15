from __future__ import annotations

import math
import time

from .constants import FIRMWARE_VERSION, HEARTBEAT_TIMEOUT_MS


class SimulatorCore:
    def __init__(self, firmware_version: str = FIRMWARE_VERSION) -> None:
        self.firmware_version = firmware_version
        self.streaming = False
        self.relay_on = False
        self._last_emit_ms = 0
        self._heartbeat_deadline_ms = 0

    def handle_command(self, command_line: str, now_ms: int | None = None) -> list[str]:
        now_ms = self._resolve_now(now_ms)
        command = command_line.strip().upper()
        if not command:
            return ["ERROR,BAD_CMD,Empty command"]

        if command == "HELLO":
            return [f"READY,{self.firmware_version}"]

        if command == "STATUS":
            return [self._status_line(now_ms)]

        if command == "HEARTBEAT":
            self._heartbeat_deadline_ms = now_ms + HEARTBEAT_TIMEOUT_MS
            return []

        if command == "STREAM,1":
            self.streaming = True
            return [self._status_line(now_ms)]

        if command == "STREAM,0":
            self.streaming = False
            return [self._status_line(now_ms)]

        if command == "RELAY,1":
            self.relay_on = True
            return [self._status_line(now_ms)]

        if command == "RELAY,0":
            self.relay_on = False
            return [self._status_line(now_ms)]

        return [f"ERROR,BAD_CMD,{command_line.strip()}"]

    def tick(self, now_ms: int | None = None) -> list[str]:
        now_ms = self._resolve_now(now_ms)
        messages: list[str] = []

        if self.relay_on and self._heartbeat_deadline_ms and now_ms > self._heartbeat_deadline_ms:
            self.relay_on = False
            messages.append(self._status_line(now_ms))

        if self.streaming and now_ms - self._last_emit_ms >= 100:
            self._last_emit_ms = now_ms
            messages.append(self._data_line(now_ms))

        return messages

    def _status_line(self, now_ms: int) -> str:
        pressure, voltage, adc = self._sample(now_ms)
        return f"STATUS,{int(self.relay_on)},{pressure:.3f},{voltage:.3f},{adc}"

    def _data_line(self, now_ms: int) -> str:
        pressure, voltage, adc = self._sample(now_ms)
        return f"DATA,{now_ms},{pressure:.3f},{voltage:.3f},{adc},{int(self.relay_on)}"

    def _sample(self, now_ms: int) -> tuple[float, float, int]:
        phase = now_ms / 1300.0
        pressure = 5.0 + (4.0 * math.sin(phase))
        pressure = max(0.0, min(10.0, pressure))
        voltage = (pressure / 10.0) * 5.0
        adc = int(round((voltage / 5.0) * 1023.0))
        return pressure, voltage, adc

    @staticmethod
    def _resolve_now(now_ms: int | None) -> int:
        if now_ms is not None:
            return now_ms
        return int(time.monotonic() * 1000)

