from __future__ import annotations

import threading
import time

from PySide6.QtCore import QObject, QTimer, Signal

from .constants import BAUD_RATE, SIMULATOR_PORT
from .simulator import SimulatorCore

try:
    import serial
    from serial.tools import list_ports
except ImportError:  # pragma: no cover - runtime dependency
    serial = None
    list_ports = None


class BaseTransport(QObject):
    line_received = Signal(str)
    connection_changed = Signal(bool, str)
    error = Signal(str)


class SerialTransport(BaseTransport):
    def __init__(self, port: str, baud_rate: int = BAUD_RATE, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.port = port
        self.baud_rate = baud_rate
        self._serial = None
        self._stop_event = threading.Event()
        self._write_lock = threading.Lock()
        self._connected = False

    def open(self) -> bool:
        if serial is None:
            self.error.emit("pyserial is not installed. Run pip install -r desktop\\requirements.txt")
            return False

        try:
            self._serial = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=0.1,
                write_timeout=0.5,
            )
        except Exception as exc:  # pragma: no cover - hardware path
            self.error.emit(f"Failed to open {self.port}: {exc}")
            return False

        self._stop_event.clear()
        reader = threading.Thread(target=self._read_loop, name=f"serial-reader-{self.port}", daemon=True)
        reader.start()
        self._emit_connection_state(True)
        return True

    def write_line(self, line: str) -> None:
        payload = (line.strip() + "\n").encode("utf-8")
        with self._write_lock:
            if self._serial is None or not self._serial.is_open:
                raise RuntimeError("Serial port is not open.")
            self._serial.write(payload)

    def close(self) -> None:
        self._drop_connection()

    def _read_loop(self) -> None:
        while not self._stop_event.is_set():
            current = self._serial
            if current is None:
                break
            try:
                raw_line = current.readline()
            except Exception as exc:  # pragma: no cover - hardware path
                self.error.emit(f"Serial read error on {self.port}: {exc}")
                break
            if not raw_line:
                continue
            text = raw_line.decode("utf-8", errors="replace").strip()
            if text:
                self.line_received.emit(text)

        if not self._stop_event.is_set():
            self._drop_connection()

    def _drop_connection(self) -> None:
        self._stop_event.set()
        with self._write_lock:
            current = self._serial
            self._serial = None
        if current is not None:
            try:
                current.close()
            except Exception:
                pass
        self._emit_connection_state(False)

    def _emit_connection_state(self, connected: bool) -> None:
        if self._connected == connected:
            return
        self._connected = connected
        self.connection_changed.emit(connected, self.port)


class SimulatorTransport(BaseTransport):
    def __init__(self, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.port = SIMULATOR_PORT
        self._core = SimulatorCore()
        self._timer = QTimer(self)
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._on_tick)
        self._connected = False

    def open(self) -> bool:
        self._timer.start()
        self._connected = True
        self.connection_changed.emit(True, self.port)
        return True

    def write_line(self, line: str) -> None:
        for response in self._core.handle_command(line, self._now_ms()):
            self.line_received.emit(response)

    def close(self) -> None:
        if self._timer.isActive():
            self._timer.stop()
        if self._connected:
            self._connected = False
            self.connection_changed.emit(False, self.port)

    def _on_tick(self) -> None:
        for response in self._core.tick(self._now_ms()):
            self.line_received.emit(response)

    @staticmethod
    def _now_ms() -> int:
        return int(time.monotonic() * 1000)


def list_available_ports() -> list[str]:
    ports = [SIMULATOR_PORT]
    if list_ports is None:
        return ports
    detected = sorted(port.device for port in list_ports.comports())
    return ports + detected

