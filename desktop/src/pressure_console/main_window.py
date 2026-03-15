from __future__ import annotations

import time

from PySide6.QtCore import QEasingCurve, QPropertyAnimation, QThread, QTimer, Qt
from PySide6.QtGui import QCloseEvent, QFont
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from .constants import (
    HANDSHAKE_RETRY_INTERVAL_MS,
    HANDSHAKE_TIMEOUT_MS,
    HEARTBEAT_INTERVAL_MS,
    MAX_PRESSURE_BAR,
    PARSE_ERROR_LIMIT,
    SIMULATOR_PORT,
)
from .firmware_worker import FirmwareUpdateWorker
from .pressure import RollingWindowBuffer
from .protocol import (
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
from .session import LinkPhase, SessionState
from .transport import SerialTransport, SimulatorTransport, list_available_ports
from .ui_theme import COLORS
from .widgets.pressure_display import PressureDisplayWidget
from .widgets.status_lamp import StatusLampWidget
from .widgets.trend_plot import PressureTrendWidget


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Pressure Control Console")
        self.resize(1480, 920)

        self._session = SessionState()
        self._transport = None
        self._firmware_thread: QThread | None = None
        self._firmware_worker: FirmwareUpdateWorker | None = None
        self._trend_buffer = RollingWindowBuffer()
        self._relay_on = False
        self._boot_animation: QPropertyAnimation | None = None
        self._handshake_attempts = 0

        self._heartbeat_timer = QTimer(self)
        self._heartbeat_timer.setInterval(HEARTBEAT_INTERVAL_MS)
        self._heartbeat_timer.timeout.connect(self._send_heartbeat)

        self._handshake_timer = QTimer(self)
        self._handshake_timer.setSingleShot(True)
        self._handshake_timer.setInterval(HANDSHAKE_TIMEOUT_MS)
        self._handshake_timer.timeout.connect(self._handle_handshake_timeout)

        self._handshake_retry_timer = QTimer(self)
        self._handshake_retry_timer.setInterval(HANDSHAKE_RETRY_INTERVAL_MS)
        self._handshake_retry_timer.timeout.connect(self._send_handshake_probe)

        self._build_ui()
        self._refresh_ports()
        self._update_session_ui()
        self._log_event("Cockpit console initialized.")

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._boot_animation is None:
            self.setWindowOpacity(0.0)
            self._boot_animation = QPropertyAnimation(self, b"windowOpacity", self)
            self._boot_animation.setDuration(900)
            self._boot_animation.setStartValue(0.0)
            self._boot_animation.setEndValue(1.0)
            self._boot_animation.setEasingCurve(QEasingCurve.OutCubic)
            self._boot_animation.start()
            self._pressure_display.arm_boot_sweep()

    def closeEvent(self, event: QCloseEvent) -> None:
        self._disconnect_transport("Shutdown sequence")
        if self._firmware_thread is not None:
            self._firmware_thread.quit()
            self._firmware_thread.wait(1500)
        super().closeEvent(event)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(18)

        layout.addLayout(self._build_top_row())
        layout.addLayout(self._build_body_row())

    def _build_top_row(self) -> QHBoxLayout:
        top_row = QHBoxLayout()
        top_row.setSpacing(18)
        top_row.addWidget(self._build_link_panel(), 4)
        top_row.addWidget(self._build_system_panel(), 3)
        return top_row

    def _build_body_row(self) -> QHBoxLayout:
        body = QHBoxLayout()
        body.setSpacing(18)

        center_column = QVBoxLayout()
        center_column.setSpacing(18)
        center_column.addWidget(self._build_pressure_panel(), 7)
        center_column.addWidget(self._build_trend_panel(), 4)

        body.addLayout(center_column, 7)
        body.addWidget(self._build_control_panel(), 3)
        return body

    def _build_link_panel(self) -> QWidget:
        panel, layout = self._create_panel("Link Control")

        control_row = QHBoxLayout()
        control_row.setSpacing(12)

        self._port_combo = QComboBox()
        self._port_combo.setMinimumWidth(200)

        self._refresh_button = QPushButton("REFRESH")
        self._refresh_button.clicked.connect(self._refresh_ports)

        self._connect_button = QPushButton("CONNECT")
        self._connect_button.setProperty("accent", True)
        self._connect_button.clicked.connect(self._toggle_connection)

        control_row.addWidget(self._port_combo, 3)
        control_row.addWidget(self._refresh_button, 1)
        control_row.addWidget(self._connect_button, 1)
        layout.addLayout(control_row)

        status_row = QHBoxLayout()
        status_row.setSpacing(12)
        self._link_badge = self._build_badge()
        self._firmware_badge = self._build_badge()
        status_row.addWidget(self._link_badge)
        status_row.addWidget(self._firmware_badge)
        status_row.addStretch(1)
        layout.addLayout(status_row)
        return panel

    def _build_system_panel(self) -> QWidget:
        panel, layout = self._create_panel("System Control")

        row = QHBoxLayout()
        row.setSpacing(12)

        self._firmware_button = QPushButton("FIRMWARE UPDATE")
        self._firmware_button.setProperty("accent", True)
        self._firmware_button.clicked.connect(self._start_firmware_update)

        self._pressure_label = self._build_metric_label("Pressure", "0.00 bar")
        self._voltage_label = self._build_metric_label("Voltage", "0.000 V")
        self._adc_label = self._build_metric_label("ADC", "0000")

        row.addWidget(self._pressure_label)
        row.addWidget(self._voltage_label)
        row.addWidget(self._adc_label)
        row.addStretch(1)
        row.addWidget(self._firmware_button)
        layout.addLayout(row)
        return panel

    def _build_pressure_panel(self) -> QWidget:
        panel, layout = self._create_panel("Pressure Core")
        self._pressure_display = PressureDisplayWidget()
        layout.addWidget(self._pressure_display)
        return panel

    def _build_trend_panel(self) -> QWidget:
        panel, layout = self._create_panel("Trend Window // Latest 10 Seconds")
        self._trend_plot = PressureTrendWidget()
        self._trend_plot.setMinimumHeight(260)
        layout.addWidget(self._trend_plot)
        return panel

    def _build_control_panel(self) -> QWidget:
        panel, layout = self._create_panel("Solenoid Control")
        panel.setMinimumWidth(340)

        lamp_row = QHBoxLayout()
        lamp_row.setSpacing(16)
        self._status_lamp = StatusLampWidget()
        lamp_caption = QLabel("Relay State\nSafe-off supervised")
        lamp_caption.setProperty("muted", True)
        lamp_caption.setFont(QFont("Bahnschrift SemiCondensed", 12))
        lamp_row.addWidget(self._status_lamp, 0, Qt.AlignTop)
        lamp_row.addWidget(lamp_caption, 1, Qt.AlignVCenter)
        layout.addLayout(lamp_row)

        self._solenoid_button = QPushButton("SOLENOID OFF")
        self._solenoid_button.setProperty("solenoid", True)
        self._solenoid_button.setCheckable(True)
        self._solenoid_button.clicked.connect(self._toggle_solenoid)
        layout.addWidget(self._solenoid_button)

        stats_grid = QGridLayout()
        stats_grid.setHorizontalSpacing(12)
        stats_grid.setVerticalSpacing(8)

        self._live_status_value = self._build_value_label("Offline")
        self._control_status_value = self._build_value_label("Locked")
        self._relay_status_value = self._build_value_label("OFF")

        stats_grid.addWidget(self._build_caption_label("Link"), 0, 0)
        stats_grid.addWidget(self._live_status_value, 0, 1)
        stats_grid.addWidget(self._build_caption_label("Control"), 1, 0)
        stats_grid.addWidget(self._control_status_value, 1, 1)
        stats_grid.addWidget(self._build_caption_label("Solenoid"), 2, 0)
        stats_grid.addWidget(self._relay_status_value, 2, 1)
        layout.addLayout(stats_grid)

        log_title = QLabel("Event Log")
        log_title.setProperty("panelTitle", True)
        layout.addWidget(log_title)

        self._event_log = QPlainTextEdit()
        self._event_log.setReadOnly(True)
        self._event_log.document().setMaximumBlockCount(250)
        self._event_log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout.addWidget(self._event_log, 1)
        return panel

    def _toggle_connection(self) -> None:
        if self._transport is not None:
            self._disconnect_transport("Operator disconnected link")
            return

        port = self._port_combo.currentText().strip()
        if not port:
            QMessageBox.warning(self, "No Port", "Select a COM port or SIMULATOR before connecting.")
            return

        self._trend_buffer.clear()
        self._trend_plot.set_series([], [])
        self._session.begin_connect(port)
        self._update_session_ui()

        transport = SimulatorTransport(self) if port == SIMULATOR_PORT else SerialTransport(port, parent=self)
        transport.line_received.connect(self._handle_protocol_line)
        transport.connection_changed.connect(self._handle_connection_change)
        transport.error.connect(self._handle_transport_error)

        if not transport.open():
            self._session.mark_fault(f"Failed to open {port}")
            self._update_session_ui()
            return

        self._transport = transport
        self._handshake_attempts = 0
        self._log_event(f"Link opening on {port}.")
        self._handshake_timer.start()
        self._handshake_retry_timer.start()
        self._send_handshake_probe()

    def _disconnect_transport(self, reason: str | None = None) -> None:
        self._heartbeat_timer.stop()
        self._handshake_timer.stop()
        self._handshake_retry_timer.stop()

        if reason:
            self._log_event(reason)

        if self._transport is not None:
            try:
                self._send_command(relay_command(False), log_command=False, suppress_errors=True)
                self._send_command(stream_command(False), log_command=False, suppress_errors=True)
            finally:
                transport = self._transport
                transport.close()
                self._transport = None

        self._relay_on = False
        self._handshake_attempts = 0
        self._session.mark_disconnect()
        self._status_lamp.set_state(False)
        self._pressure_display.set_connection_state(False)
        self._update_session_ui()

    def _handle_connection_change(self, connected: bool, port: str) -> None:
        if connected:
            self._log_event(f"Transport opened on {port}. Waiting for READY handshake.")
            return

        self._heartbeat_timer.stop()
        self._handshake_timer.stop()
        self._handshake_retry_timer.stop()
        self._relay_on = False
        self._handshake_attempts = 0
        self._status_lamp.set_state(False)
        self._pressure_display.set_connection_state(False)
        self._session.mark_disconnect()
        self._transport = None
        self._update_session_ui()
        self._log_event(f"Transport closed on {port}.")

    def _handle_transport_error(self, message: str) -> None:
        self._log_event(message)
        if self._session.phase == LinkPhase.CONNECTING:
            self._session.mark_fault(message)
            self._update_session_ui()

    def _handle_protocol_line(self, line: str) -> None:
        try:
            message = parse_line(line)
        except ValueError as exc:
            if self._session.phase == LinkPhase.CONNECTING:
                self._log_event(f"Ignoring pre-handshake serial noise: {exc}")
                return
            locked = self._session.register_parse_error(PARSE_ERROR_LIMIT)
            self._log_event(f"Protocol parse error: {exc}")
            if locked:
                self._log_event("Control lock engaged after repeated parse errors.")
            self._update_session_ui()
            return

        if isinstance(message, ReadyMessage):
            self._handshake_timer.stop()
            self._handshake_retry_timer.stop()
            self._session.mark_ready(message.firmware_version)
            self._pressure_display.set_connection_state(True)
            self._update_session_ui()
            self._log_event(f"Handshake complete. Firmware {message.firmware_version}.")
            self._send_command(stream_command(True), log_command=False)
            self._send_command(status_command(), log_command=False)
            self._heartbeat_timer.start()
            return

        if isinstance(message, StatusMessage):
            self._apply_telemetry(
                pressure_bar=message.pressure_bar,
                voltage=message.voltage,
                adc=message.adc,
                relay_on=message.relay_on,
                sample_time=time.monotonic(),
            )
            return

        if isinstance(message, DataMessage):
            self._apply_telemetry(
                pressure_bar=message.pressure_bar,
                voltage=message.voltage,
                adc=message.adc,
                relay_on=message.relay_on,
                sample_time=message.timestamp_ms / 1000.0,
            )
            return

        if isinstance(message, ErrorMessage):
            self._log_event(f"Device error [{message.code}]: {message.message}")

    def _apply_telemetry(
        self,
        pressure_bar: float,
        voltage: float,
        adc: int,
        relay_on: bool,
        sample_time: float,
    ) -> None:
        bounded_pressure = max(0.0, min(pressure_bar, MAX_PRESSURE_BAR))
        self._trend_buffer.append(sample_time, bounded_pressure)
        x_values, y_values = self._trend_buffer.relative_points()
        self._trend_plot.set_series(x_values, y_values)

        self._pressure_display.set_telemetry(bounded_pressure, voltage, adc)
        self._pressure_label.setText(f"Pressure\n{bounded_pressure:0.2f} bar")
        self._voltage_label.setText(f"Voltage\n{voltage:0.3f} V")
        self._adc_label.setText(f"ADC\n{adc:04d}")

        self._relay_on = relay_on
        self._relay_status_value.setText("ON" if relay_on else "OFF")
        self._status_lamp.set_state(relay_on, fault=self._session.phase == LinkPhase.FAULT)

        blocked = self._solenoid_button.blockSignals(True)
        self._solenoid_button.setChecked(relay_on)
        self._solenoid_button.setText("SOLENOID ON" if relay_on else "SOLENOID OFF")
        self._solenoid_button.blockSignals(blocked)

    def _toggle_solenoid(self, checked: bool) -> None:
        if self._transport is None or not self._session.controls_enabled:
            self._log_event("Control request ignored because the link is not ready.")
            return
        if self._send_command(relay_command(checked), log_command=True):
            requested = "ON" if checked else "OFF"
            self._log_event(f"Operator requested solenoid {requested}.")

    def _send_heartbeat(self) -> None:
        self._send_command(heartbeat_command(), log_command=False, suppress_errors=True)

    def _send_handshake_probe(self) -> None:
        if self._transport is None or self._session.phase != LinkPhase.CONNECTING:
            return

        self._handshake_attempts += 1
        if self._handshake_attempts == 1:
            self._send_command(hello_command(), log_command=True)
            return

        self._send_command(hello_command(), log_command=False, suppress_errors=True)
        if self._handshake_attempts in (3, 6):
            self._log_event(f"Retrying HELLO handshake ({self._handshake_attempts}).")

    def _handle_handshake_timeout(self) -> None:
        self._handshake_retry_timer.stop()
        self._log_event(
            "Handshake timed out waiting for READY after repeated HELLO attempts. "
            "Check that the Uno firmware is uploaded and that the selected COM port is correct."
        )
        self._session.mark_fault("Handshake timed out")
        self._update_session_ui()
        self._disconnect_transport("Link aborted after handshake timeout")

    def _send_command(self, command: str, log_command: bool, suppress_errors: bool = False) -> bool:
        if self._transport is None:
            return False
        try:
            self._transport.write_line(command)
        except Exception as exc:
            if not suppress_errors:
                self._log_event(f"Command failed: {exc}")
            return False
        if log_command:
            self._log_event(f"TX > {command}")
        return True

    def _refresh_ports(self) -> None:
        current = self._port_combo.currentText()
        self._port_combo.clear()
        for port in list_available_ports():
            self._port_combo.addItem(port)
        if current:
            index = self._port_combo.findText(current)
            if index >= 0:
                self._port_combo.setCurrentIndex(index)
        self._log_event("Port list refreshed.")

    def _start_firmware_update(self) -> None:
        if self._firmware_thread is not None:
            return

        port = self._port_combo.currentText().strip()
        if not port or port == SIMULATOR_PORT:
            QMessageBox.warning(self, "Firmware Update", "Select a physical COM port before updating firmware.")
            return

        if self._transport is not None:
            self._disconnect_transport("Disconnecting link before firmware update")

        self._firmware_thread = QThread(self)
        self._firmware_worker = FirmwareUpdateWorker(port)
        self._firmware_worker.moveToThread(self._firmware_thread)
        self._firmware_thread.started.connect(self._firmware_worker.run)
        self._firmware_worker.progress.connect(self._log_event)
        self._firmware_worker.finished.connect(self._handle_firmware_success)
        self._firmware_worker.failed.connect(self._handle_firmware_failure)
        self._firmware_worker.finished.connect(self._cleanup_firmware_worker)
        self._firmware_worker.failed.connect(self._cleanup_firmware_worker)
        self._firmware_thread.finished.connect(self._firmware_thread.deleteLater)

        self._firmware_button.setEnabled(False)
        self._connect_button.setEnabled(False)
        self._log_event(f"Firmware update started on {port}.")
        self._firmware_thread.start()

    def _handle_firmware_success(self) -> None:
        self._log_event("Firmware update completed successfully.")
        QMessageBox.information(self, "Firmware Update", "Firmware compile and upload completed.")

    def _handle_firmware_failure(self, message: str) -> None:
        self._log_event(f"Firmware update failed: {message}")
        QMessageBox.critical(
            self,
            "Firmware Update Failed",
            "Firmware update did not complete.\n\n"
            f"{message}\n\n"
            "Confirm arduino-cli and the arduino:avr core are installed.",
        )

    def _cleanup_firmware_worker(self) -> None:
        if self._firmware_thread is not None:
            self._firmware_thread.quit()
            self._firmware_thread.wait(1500)
            self._firmware_thread = None
        if self._firmware_worker is not None:
            self._firmware_worker.deleteLater()
            self._firmware_worker = None
        self._firmware_button.setEnabled(True)
        self._connect_button.setEnabled(True)

    def _update_session_ui(self) -> None:
        phase = self._session.phase
        if phase == LinkPhase.CONNECTED:
            self._set_badge_style(self._link_badge, "LINK READY", "#12374b", COLORS["cyan"])
        elif phase == LinkPhase.CONNECTING:
            self._set_badge_style(self._link_badge, "LINKING", "#3a2e10", COLORS["amber"])
        elif phase == LinkPhase.FAULT:
            self._set_badge_style(self._link_badge, "FAULT", "#4a1822", COLORS["danger"])
        else:
            self._set_badge_style(self._link_badge, "OFFLINE", "#182736", COLORS["muted"])

        self._set_badge_style(self._firmware_badge, f"FW {self._session.firmware_version}", "#102235", COLORS["amber_soft"])
        self._connect_button.setText("DISCONNECT" if self._transport is not None else "CONNECT")
        self._solenoid_button.setEnabled(
            self._transport is not None and phase == LinkPhase.CONNECTED and self._session.controls_enabled
        )
        self._control_status_value.setText("Armed" if self._session.controls_enabled else "Locked")
        self._live_status_value.setText(phase.value.capitalize())

    def _create_panel(self, title: str) -> tuple[QWidget, QVBoxLayout]:
        panel = QFrame()
        panel.setProperty("hudPanel", True)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(14)

        title_label = QLabel(title)
        title_label.setProperty("panelTitle", True)
        layout.addWidget(title_label)
        return panel, layout

    @staticmethod
    def _build_badge() -> QLabel:
        badge = QLabel()
        badge.setContentsMargins(12, 6, 12, 6)
        badge.setMinimumHeight(30)
        badge.setAlignment(Qt.AlignCenter)
        return badge

    @staticmethod
    def _build_metric_label(title: str, value: str) -> QLabel:
        label = QLabel(f"{title}\n{value}")
        label.setAlignment(Qt.AlignCenter)
        label.setMinimumWidth(120)
        label.setStyleSheet(
            f"background: {COLORS['panel_alt']}; border: 1px solid {COLORS['cyan_dim']};"
            "border-radius: 14px; padding: 10px; font-weight: 700;"
        )
        return label

    @staticmethod
    def _build_caption_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setProperty("muted", True)
        return label

    @staticmethod
    def _build_value_label(text: str) -> QLabel:
        label = QLabel(text)
        label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        label.setFont(QFont("Bahnschrift SemiCondensed", 11, QFont.DemiBold))
        return label

    @staticmethod
    def _set_badge_style(label: QLabel, text: str, background: str, foreground: str) -> None:
        label.setText(text)
        label.setStyleSheet(
            f"background: {background}; color: {foreground}; border: 1px solid {foreground};"
            "border-radius: 12px; padding: 4px 12px; font-weight: 700;"
        )

    def _log_event(self, message: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self._event_log.appendPlainText(f"[{timestamp}] {message}")
