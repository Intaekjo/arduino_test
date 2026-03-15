from __future__ import annotations

from dataclasses import dataclass
from typing import Union


@dataclass(frozen=True, slots=True)
class ReadyMessage:
    firmware_version: str


@dataclass(frozen=True, slots=True)
class StatusMessage:
    relay_on: bool
    pressure_bar: float
    voltage: float
    adc: int


@dataclass(frozen=True, slots=True)
class DataMessage:
    timestamp_ms: int
    pressure_bar: float
    voltage: float
    adc: int
    relay_on: bool


@dataclass(frozen=True, slots=True)
class ErrorMessage:
    code: str
    message: str


ProtocolMessage = Union[ReadyMessage, StatusMessage, DataMessage, ErrorMessage]


def parse_line(line: str) -> ProtocolMessage:
    cleaned = line.strip()
    if not cleaned:
        raise ValueError("Received an empty protocol line.")

    if cleaned.startswith("ERROR,"):
        _, code, message = cleaned.split(",", 2)
        return ErrorMessage(code=code.strip(), message=message.strip())

    parts = [part.strip() for part in cleaned.split(",")]
    command = parts[0].upper()

    if command == "READY" and len(parts) == 2:
        return ReadyMessage(firmware_version=parts[1])

    if command == "STATUS" and len(parts) == 5:
        return StatusMessage(
            relay_on=_parse_bool(parts[1]),
            pressure_bar=float(parts[2]),
            voltage=float(parts[3]),
            adc=int(parts[4]),
        )

    if command == "DATA" and len(parts) == 6:
        return DataMessage(
            timestamp_ms=int(parts[1]),
            pressure_bar=float(parts[2]),
            voltage=float(parts[3]),
            adc=int(parts[4]),
            relay_on=_parse_bool(parts[5]),
        )

    raise ValueError(f"Unsupported protocol line: {cleaned}")


def format_command(command: str, *parts: object) -> str:
    payload = [command.upper(), *[str(part) for part in parts]]
    return ",".join(payload)


def hello_command() -> str:
    return "HELLO"


def stream_command(enabled: bool) -> str:
    return format_command("STREAM", 1 if enabled else 0)


def status_command() -> str:
    return "STATUS"


def relay_command(enabled: bool) -> str:
    return format_command("RELAY", 1 if enabled else 0)


def heartbeat_command() -> str:
    return "HEARTBEAT"


def _parse_bool(value: str) -> bool:
    if value == "1":
        return True
    if value == "0":
        return False
    raise ValueError(f"Expected relay flag 0 or 1, received {value!r}")

