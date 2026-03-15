from __future__ import annotations

import subprocess

from PySide6.QtCore import QObject, Signal, Slot

from .firmware import (
    build_firmware_commands,
    default_firmware_paths,
    ensure_arduino_cli,
    project_root,
    resolve_arduino_cli,
    run_cli_command,
)


class FirmwareUpdateWorker(QObject):
    progress = Signal(str)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, port: str, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.port = port

    @Slot()
    def run(self) -> None:
        try:
            ensure_arduino_cli()
            cli_path = resolve_arduino_cli()
            paths = default_firmware_paths()
            paths.build_dir.mkdir(parents=True, exist_ok=True)
            command_set = build_firmware_commands(port=self.port, paths=paths, cli_path=cli_path)
            self._run_step("Compile", command_set.compile_command)
            self._run_step("Upload", command_set.upload_command)
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))

    def _run_step(self, label: str, command: list[str]) -> None:
        self.progress.emit(f"{label}: {subprocess.list2cmdline(command)}")
        result = run_cli_command(command, cwd=project_root())
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if stdout:
            for line in stdout.splitlines():
                self.progress.emit(f"{label}: {line}")
        if stderr:
            for line in stderr.splitlines():
                self.progress.emit(f"{label}: {line}")
        if result.returncode != 0:
            raise RuntimeError(f"{label} failed with exit code {result.returncode}.")
