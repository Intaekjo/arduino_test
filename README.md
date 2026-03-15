# Arduino Uno Pressure Control Console

Windows desktop control console for an Arduino Uno pressure monitoring and
solenoid control setup.

## Features

- Gundam-inspired HUD desktop GUI
- Real-time 0-10 bar pressure display with a 10 second trend view
- Vacuum tube inspired central pressure indicator
- Manual solenoid ON/OFF control with safe-off shutdown behavior
- COM port connect/disconnect flow
- Firmware compile and upload through `arduino-cli`
- Built-in simulator for UI development without hardware

## Project Layout

- `desktop/`: Python desktop application
- `firmware/uno_controller/`: Arduino Uno firmware
- `tests/`: Python tests for protocol and controller logic
- `tools/`: PowerShell helper scripts

## Desktop Dependencies

Install the Python packages:

```powershell
python -m pip install -r desktop\requirements.txt
```

## Run The Desktop App

```powershell
powershell -ExecutionPolicy Bypass -File tools\run_console.ps1
```

The COM list includes a `SIMULATOR` target for UI testing without an Arduino.

## Firmware Update Prerequisites

Install `arduino-cli` and the Uno core:

```powershell
arduino-cli core update-index
arduino-cli core install arduino:avr
```

The GUI expects `arduino-cli` to be on `PATH`.

## GitHub Release

This repo now includes a GitHub Actions workflow at `.github/workflows/release.yml`
that builds a Windows release bundle and attaches it to a GitHub Release whenever
you push a tag that starts with `v`.

Release flow:

```powershell
git tag v1.0.0
git push origin v1.0.0
```

The workflow will:

- run the Python tests
- build a Windows `PressureControlConsole` bundle with PyInstaller
- attach `PressureControlConsole-windows.zip` to the GitHub Release

You can also build the same release bundle locally:

```powershell
powershell -ExecutionPolicy Bypass -File tools\build_release.ps1
```

## Safety Note

This project assumes the software-defined OFF state should also mean the
solenoid is physically OFF. Verify the NC relay wiring on the bench before
energizing the real system. If the relay drops into an unsafe energized state
when control power is removed, rewire to a fail-safe NO path or add an
interposing relay.
