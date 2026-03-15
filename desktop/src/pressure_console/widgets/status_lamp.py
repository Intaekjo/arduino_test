from __future__ import annotations

import math

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import QWidget

from ..ui_theme import COLORS


class StatusLampWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(96, 96)
        self._active = False
        self._fault = False
        self._phase = 0.0

        self._timer = QTimer(self)
        self._timer.setInterval(33)
        self._timer.timeout.connect(self._advance_animation)
        self._timer.start()

    def set_state(self, active: bool, fault: bool = False) -> None:
        self._active = active
        self._fault = fault
        self.update()

    def _advance_animation(self) -> None:
        self._phase = (self._phase + 0.04) % 1.0
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = self.rect().adjusted(8, 8, -8, -8)
        base_color = QColor(COLORS["danger"]) if self._fault else QColor(COLORS["cyan"])
        if self._active and not self._fault:
            base_color = QColor(COLORS["amber"])

        pulse = 0.55 + (0.35 * math.sin(self._phase * math.tau))
        gradient = QRadialGradient(rect.center(), rect.width() / 2)
        gradient.setColorAt(0.0, _with_alpha(base_color, int(220 * pulse)))
        gradient.setColorAt(0.5, _with_alpha(base_color, int(120 * pulse)))
        gradient.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(rect)

        painter.setBrush(QColor("#07111a"))
        painter.setPen(QPen(_with_alpha(base_color, 200), 3))
        painter.drawEllipse(rect.adjusted(18, 18, -18, -18))


def _with_alpha(color: QColor, alpha: int) -> QColor:
    clone = QColor(color)
    clone.setAlpha(alpha)
    return clone

