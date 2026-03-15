from __future__ import annotations

from pressure_console.session import LinkPhase, SessionState


def test_session_state_transitions() -> None:
    session = SessionState()
    session.begin_connect("COM4")
    assert session.phase == LinkPhase.CONNECTING
    assert session.active_port == "COM4"
    assert session.controls_enabled is False

    session.mark_ready("1.0.0")
    assert session.phase == LinkPhase.CONNECTED
    assert session.firmware_version == "1.0.0"
    assert session.controls_enabled is True

    session.mark_disconnect()
    assert session.phase == LinkPhase.DISCONNECTED
    assert session.active_port is None


def test_session_parse_lock() -> None:
    session = SessionState()
    session.begin_connect("COM6")
    session.mark_ready("1.0.0")

    assert session.register_parse_error(3) is False
    assert session.register_parse_error(3) is False
    assert session.register_parse_error(3) is True
    assert session.controls_enabled is False
    assert session.last_error == "Protocol parsing lockout"

