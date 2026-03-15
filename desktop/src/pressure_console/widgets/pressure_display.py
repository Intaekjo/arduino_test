from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt, QRectF
from PySide6.QtGui import QColor, QFont, QLinearGradient, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..constants import MAX_PRESSURE_BAR
from ..ui_theme import COLORS


class PressureDisplayWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumHeight(300)
        self._pressure_bar = 0.0
        self._voltage = 0.0
        self._adc = 0
        self._connected = False
        self._sweep_phase = 0.0

        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(33)
        self._animation_timer.timeout.connect(self._advance_animation)
        self._animation_timer.start()

    def set_telemetry(self, pressure_bar: float, voltage: float, adc: int) -> None:
        self._pressure_bar = pressure_bar
        self._voltage = voltage
        self._adc = adc
        self.update()

    def set_connection_state(self, connected: bool) -> None:
        self._connected = connected
        self.update()

    def arm_boot_sweep(self) -> None:
        self._sweep_phase = 0.0
        self.update()

    def _advance_animation(self) -> None:
        self._sweep_phase = (self._sweep_phase + 0.03) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        frame = self.rect().adjusted(12, 12, -12, -12)
        background = QLinearGradient(frame.topLeft(), frame.bottomLeft())
        background.setColorAt(0.0, QColor("#102235"))
        background.setColorAt(1.0, QColor("#07111a"))
        painter.setBrush(background)
        painter.setPen(QPen(QColor(COLORS["cyan_dim"]), 2))
        painter.drawRoundedRect(frame, 24, 24)

        self._draw_corner_accents(painter, frame)
        self._draw_scan_lines(painter, frame)
        self._draw_sweep(painter, frame)
        self._draw_gauge(painter, frame)
        self._draw_digits(painter, frame)
        self._draw_status(painter, frame)

    def _draw_corner_accents(self, painter: QPainter, frame) -> None:
        pen = QPen(QColor(COLORS["cyan"]), 3)
        painter.setPen(pen)
        corner = 32
        painter.drawLine(frame.left(), frame.top() + corner, frame.left(), frame.top())
        painter.drawLine(frame.left(), frame.top(), frame.left() + corner, frame.top())
        painter.drawLine(frame.right() - corner, frame.top(), frame.right(), frame.top())
        painter.drawLine(frame.right(), frame.top(), frame.right(), frame.top() + corner)
        painter.drawLine(frame.left(), frame.bottom() - corner, frame.left(), frame.bottom())
        painter.drawLine(frame.left(), frame.bottom(), frame.left() + corner, frame.bottom())
        painter.drawLine(frame.right() - corner, frame.bottom(), frame.right(), frame.bottom())
        painter.drawLine(frame.right(), frame.bottom() - corner, frame.right(), frame.bottom())

    def _draw_scan_lines(self, painter: QPainter, frame) -> None:
        pen = QPen(QColor(18, 52, 68, 60), 1)
        painter.setPen(pen)
        for y in range(frame.top() + 10, frame.bottom(), 10):
            painter.drawLine(frame.left() + 8, y, frame.right() - 8, y)

    def _draw_sweep(self, painter: QPainter, frame) -> None:
        sweep_x = frame.left() + int(frame.width() * self._sweep_phase)
        gradient = QLinearGradient(sweep_x - 40, frame.top(), sweep_x + 40, frame.top())
        gradient.setColorAt(0.0, QColor(0, 0, 0, 0))
        gradient.setColorAt(0.5, QColor(87, 227, 255, 70))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawRect(frame)

    def _draw_gauge(self, painter: QPainter, frame) -> None:
        _, _, info_rect, center_x, center_y, radius = self._layout_metrics(frame)
        arc_rect = QRectF(center_x - radius, center_y - radius, radius * 2.0, radius * 2.0)

        painter.setPen(QPen(QColor(COLORS["cyan_dim"]), 10))
        painter.drawArc(arc_rect, 225 * 16, -270 * 16)

        painter.setPen(QPen(QColor(COLORS["cyan"]), 2))
        for tick in range(11):
            ratio = tick / 10.0
            angle = math.radians(225 - (270 * ratio))
            outer_x = center_x + math.cos(angle) * radius
            outer_y = center_y - math.sin(angle) * radius
            inner_x = center_x + math.cos(angle) * (radius - 18)
            inner_y = center_y - math.sin(angle) * (radius - 18)
            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))

        fill_span = int((self._pressure_bar / MAX_PRESSURE_BAR) * -270 * 16)
        painter.setPen(QPen(QColor(COLORS["amber"]), 8))
        painter.drawArc(arc_rect, 225 * 16, fill_span)

        pointer_ratio = self._pressure_bar / MAX_PRESSURE_BAR
        pointer_angle = math.radians(225 - (270 * pointer_ratio))
        pointer_x = center_x + math.cos(pointer_angle) * (radius - 24)
        pointer_y = center_y - math.sin(pointer_angle) * (radius - 24)
        painter.setPen(QPen(QColor(COLORS["amber_soft"]), 3))
        painter.drawLine(center_x, center_y, int(pointer_x), int(pointer_y))
        painter.setBrush(QColor(COLORS["amber"]))
        painter.drawEllipse(center_x - 6, center_y - 6, 12, 12)

        painter.setFont(QFont("Consolas", 11))
        painter.setPen(QColor(COLORS["muted"]))
        painter.drawText(
            info_rect,
            Qt.AlignLeft | Qt.AlignVCenter,
            f"VOLT {self._voltage:0.3f}    ADC {self._adc:04d}",
        )

    def _draw_digits(self, painter: QPainter, frame) -> None:
        number_rect, unit_rect, _, _, _, _ = self._layout_metrics(frame)
        digit_size = max(34, min(58, int(frame.height() * 0.16)))
        unit_size = max(15, min(18, int(digit_size * 0.30)))
        digit_font = QFont("Bahnschrift SemiCondensed", digit_size, QFont.Bold)
        unit_font = QFont("Bahnschrift SemiCondensed", unit_size, QFont.DemiBold)

        number = f"{self._pressure_bar:04.2f}"
        self._draw_glow_text(
            painter,
            number_rect,
            number,
            digit_font,
            QColor(COLORS["amber"]),
            Qt.AlignCenter,
        )

        painter.setFont(unit_font)
        painter.setPen(QColor(COLORS["amber_soft"]))
        painter.drawText(unit_rect, Qt.AlignHCenter | Qt.AlignTop, "BAR")

    def _draw_status(self, painter: QPainter, frame) -> None:
        painter.setFont(QFont("Bahnschrift SemiCondensed", 12, QFont.DemiBold))
        state_text = "LIVE LINK" if self._connected else "STANDBY"
        state_color = QColor(COLORS["cyan"]) if self._connected else QColor(COLORS["muted"])
        painter.setPen(state_color)
        painter.drawText(frame.adjusted(24, 18, -24, -18), Qt.AlignLeft | Qt.AlignTop, state_text)

        painter.setPen(QColor(COLORS["cyan_dim"]))
        painter.drawText(
            frame.adjusted(24, 18, -24, -18),
            Qt.AlignRight | Qt.AlignTop,
            "PRESSURE MONITOR // RX-UNO",
        )

    def _draw_glow_text(
        self,
        painter: QPainter,
        rect,
        text: str,
        font: QFont,
        color: QColor,
        alignment: Qt.AlignmentFlag,
    ) -> None:
        painter.setFont(font)
        for offset, alpha in ((4, 40), (2, 80), (1, 120)):
            glow = QColor(color)
            glow.setAlpha(alpha)
            painter.setPen(glow)
            painter.drawText(rect.adjusted(-offset, 0, -offset, 0), alignment, text)
            painter.drawText(rect.adjusted(offset, 0, offset, 0), alignment, text)
            painter.drawText(rect.adjusted(0, -offset, 0, -offset), alignment, text)
            painter.drawText(rect.adjusted(0, offset, 0, offset), alignment, text)
        painter.setPen(color)
        painter.drawText(rect, alignment, text)

    def _layout_metrics(self, frame) -> tuple[QRectF, QRectF, QRectF, float, float, float]:
        number_top = frame.top() + max(28, int(frame.height() * 0.08))
        number_height = max(72, int(frame.height() * 0.22))
        number_rect = QRectF(frame.left() + 36, number_top, frame.width() - 72, number_height)

        unit_rect = QRectF(frame.left() + 36, number_rect.bottom() + 4, frame.width() - 72, 28)
        info_rect = QRectF(frame.left() + 24, frame.bottom() - 42, frame.width() - 48, 18)

        gauge_top = unit_rect.bottom() + 18
        gauge_bottom = info_rect.top() - 12
        radius = max(24.0, min(frame.width() * 0.18, max(0.0, (gauge_bottom - gauge_top) / 2.0)))
        center_x = float(frame.center().x())
        center_y = gauge_top + radius
        return number_rect, unit_rect, info_rect, center_x, center_y, radius
