from __future__ import annotations

import pytest

from pressure_console.protocol import (
    DataMessage,
    ErrorMessage,
    ReadyMessage,
    StatusMessage,
    heartbeat_command,
    hello_command,
    parse_line,
    relay_command,
    status_command,
    stream_command,
)


def test_parse_ready_message() -> None:
    message = parse_line("READY,1.2.3")
    assert message == ReadyMessage(firmware_version="1.2.3")


def test_parse_status_message() -> None:
    message = parse_line("STATUS,1,6.250,3.125,640")
    assert message == StatusMessage(relay_on=True, pressure_bar=6.25, voltage=3.125, adc=640)


def test_parse_data_message() -> None:
    message = parse_line("DATA,1250,4.200,2.100,430,0")
    assert message == DataMessage(
        timestamp_ms=1250,
        pressure_bar=4.2,
        voltage=2.1,
        adc=430,
        relay_on=False,
    )


def test_parse_error_message_with_commas() -> None:
    message = parse_line("ERROR,BAD_CMD,RELAY,2")
    assert message == ErrorMessage(code="BAD_CMD", message="RELAY,2")


def test_parse_invalid_line_raises() -> None:
    with pytest.raises(ValueError):
        parse_line("UNKNOWN,1")


def test_command_helpers() -> None:
    assert hello_command() == "HELLO"
    assert stream_command(True) == "STREAM,1"
    assert stream_command(False) == "STREAM,0"
    assert status_command() == "STATUS"
    assert relay_command(True) == "RELAY,1"
    assert relay_command(False) == "RELAY,0"
    assert heartbeat_command() == "HEARTBEAT"

