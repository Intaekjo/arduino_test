from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
import subprocess

from .constants import DEFAULT_FQBN


@dataclass(frozen=True, slots=True)
class FirmwarePaths:
    sketch_dir: Path
    build_dir: Path


@dataclass(frozen=True, slots=True)
class FirmwareCommandSet:
    compile_command: list[str]
    upload_command: list[str]


def project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_firmware_paths(root: Path | None = None) -> FirmwarePaths:
    resolved_root = root or project_root()
    return FirmwarePaths(
        sketch_dir=resolved_root / "firmware" / "uno_controller",
        build_dir=resolved_root / ".build" / "uno_controller",
    )


def resolve_arduino_cli(cli_path: str | None = None) -> str:
    if cli_path:
        return cli_path

    discovered = shutil.which("arduino-cli")
    if discovered:
        return discovered

    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        user_install = Path(local_app_data) / "Programs" / "ArduinoCLI" / "bin" / "arduino-cli.exe"
        if user_install.exists():
            return str(user_install)

    program_files = os.environ.get("ProgramFiles")
    if program_files:
        system_install = Path(program_files) / "ArduinoCLI" / "bin" / "arduino-cli.exe"
        if system_install.exists():
            return str(system_install)

    raise FileNotFoundError(
        "arduino-cli was not found on PATH or in the default ArduinoCLI install folders."
    )


def build_compile_command(
    paths: FirmwarePaths | None = None,
    fqbn: str = DEFAULT_FQBN,
    cli_path: str = "arduino-cli",
) -> list[str]:
    resolved = paths or default_firmware_paths()
    return [
        cli_path,
        "compile",
        "--fqbn",
        fqbn,
        "--build-path",
        str(resolved.build_dir),
        str(resolved.sketch_dir),
    ]


def build_upload_command(
    port: str,
    paths: FirmwarePaths | None = None,
    fqbn: str = DEFAULT_FQBN,
    cli_path: str = "arduino-cli",
) -> list[str]:
    resolved = paths or default_firmware_paths()
    return [
        cli_path,
        "upload",
        "-p",
        port,
        "--fqbn",
        fqbn,
        "--input-dir",
        str(resolved.build_dir),
        str(resolved.sketch_dir),
    ]


def build_firmware_commands(
    port: str,
    paths: FirmwarePaths | None = None,
    fqbn: str = DEFAULT_FQBN,
    cli_path: str = "arduino-cli",
) -> FirmwareCommandSet:
    resolved = paths or default_firmware_paths()
    return FirmwareCommandSet(
        compile_command=build_compile_command(paths=resolved, fqbn=fqbn, cli_path=cli_path),
        upload_command=build_upload_command(port=port, paths=resolved, fqbn=fqbn, cli_path=cli_path),
    )


def ensure_arduino_cli() -> None:
    resolve_arduino_cli()


def run_cli_command(command: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd or project_root()),
        capture_output=True,
        text=True,
        check=False,
    )
