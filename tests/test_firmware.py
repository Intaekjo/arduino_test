from __future__ import annotations

from pathlib import Path
import subprocess

import pytest

import pressure_console.firmware as firmware


def test_build_firmware_commands() -> None:
    paths = firmware.FirmwarePaths(
        sketch_dir=Path("D:/repo/firmware/uno_controller"),
        build_dir=Path("D:/repo/.build/uno_controller"),
    )
    command_set = firmware.build_firmware_commands(port="COM7", paths=paths)

    assert command_set.compile_command == [
        "arduino-cli",
        "compile",
        "--fqbn",
        "arduino:avr:uno",
        "--build-path",
        "D:\\repo\\.build\\uno_controller",
        "D:\\repo\\firmware\\uno_controller",
    ]
    assert command_set.upload_command == [
        "arduino-cli",
        "upload",
        "-p",
        "COM7",
        "--fqbn",
        "arduino:avr:uno",
        "--input-dir",
        "D:\\repo\\.build\\uno_controller",
        "D:\\repo\\firmware\\uno_controller",
    ]


def test_ensure_arduino_cli_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(firmware.shutil, "which", lambda _: None)
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    monkeypatch.delenv("ProgramFiles", raising=False)

    with pytest.raises(FileNotFoundError):
        firmware.ensure_arduino_cli()


def test_resolve_arduino_cli_uses_localappdata_fallback(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    local_app_data = tmp_path / "AppData" / "Local"
    cli_path = local_app_data / "Programs" / "ArduinoCLI" / "bin" / "arduino-cli.exe"
    cli_path.parent.mkdir(parents=True)
    cli_path.write_bytes(b"exe")

    monkeypatch.setattr(firmware.shutil, "which", lambda _: None)
    monkeypatch.setenv("LOCALAPPDATA", str(local_app_data))
    monkeypatch.delenv("ProgramFiles", raising=False)

    assert firmware.resolve_arduino_cli() == str(cli_path)


def test_run_cli_command_uses_requested_cwd(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(command, cwd, capture_output, text, check):
        captured["command"] = command
        captured["cwd"] = cwd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["check"] = check
        return subprocess.CompletedProcess(command, 0, "ok", "")

    monkeypatch.setattr(firmware.subprocess, "run", fake_run)

    result = firmware.run_cli_command(["arduino-cli", "version"], cwd=Path("D:/repo"))
    assert result.stdout == "ok"
    assert captured["cwd"] == "D:\\repo"
    assert captured["capture_output"] is True
    assert captured["text"] is True
    assert captured["check"] is False


def test_project_root_uses_executable_directory_when_frozen(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_executable = tmp_path / "PressureControlConsole" / "PressureControlConsole.exe"
    fake_executable.parent.mkdir(parents=True)
    fake_executable.write_bytes(b"exe")

    monkeypatch.setattr(firmware.sys, "frozen", True, raising=False)
    monkeypatch.setattr(firmware.sys, "executable", str(fake_executable), raising=False)

    assert firmware.project_root() == fake_executable.parent
