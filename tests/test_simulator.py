from __future__ import annotations

from pressure_console.simulator import SimulatorCore


def test_simulator_handshake_and_streaming() -> None:
    simulator = SimulatorCore()
    assert simulator.handle_command("HELLO", now_ms=100) == ["READY,1.0.0"]

    status_lines = simulator.handle_command("STREAM,1", now_ms=100)
    assert status_lines[0].startswith("STATUS,0,")

    data_lines = simulator.tick(now_ms=250)
    assert data_lines[0].startswith("DATA,250,")


def test_simulator_heartbeat_timeout_forces_off() -> None:
    simulator = SimulatorCore()
    simulator.handle_command("RELAY,1", now_ms=0)
    simulator.handle_command("HEARTBEAT", now_ms=0)

    timeout_lines = simulator.tick(now_ms=2501)
    assert timeout_lines[0].startswith("STATUS,0,")


def test_simulator_invalid_command_returns_error() -> None:
    simulator = SimulatorCore()
    lines = simulator.handle_command("RELAY,2", now_ms=500)
    assert lines == ["ERROR,BAD_CMD,RELAY,2"]

