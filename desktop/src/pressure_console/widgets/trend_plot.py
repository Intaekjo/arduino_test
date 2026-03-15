from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from ..constants import GRAPH_WINDOW_SECONDS, MAX_PRESSURE_BAR
from ..ui_theme import COLORS

try:
    import pyqtgraph as pg
except ImportError:  # pragma: no cover - runtime dependency
    pg = None


class PressureTrendWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        if pg is None:
            self._curve = None
            fallback = QLabel("Install pyqtgraph to enable the live trend display.")
            fallback.setAlignment(Qt.AlignCenter)
            layout.addWidget(fallback)
            return

        plot = pg.PlotWidget()
        plot.setBackground((0, 0, 0, 0))
        plot.showGrid(x=True, y=True, alpha=0.2)
        plot.setMenuEnabled(False)
        plot.hideButtons()

        plot_item = plot.getPlotItem()
        plot_item.setClipToView(True)
        plot_item.setLimits(xMin=-GRAPH_WINDOW_SECONDS, xMax=0, yMin=0, yMax=MAX_PRESSURE_BAR)
        plot_item.setXRange(-GRAPH_WINDOW_SECONDS, 0, padding=0.02)
        plot_item.setYRange(0, MAX_PRESSURE_BAR, padding=0.05)
        plot_item.getAxis("bottom").setLabel("Seconds", color=COLORS["muted"])
        plot_item.getAxis("left").setLabel("bar", color=COLORS["muted"])
        plot_item.getAxis("bottom").setPen(pg.mkPen(COLORS["cyan_dim"], width=1))
        plot_item.getAxis("left").setPen(pg.mkPen(COLORS["cyan_dim"], width=1))
        plot_item.getAxis("bottom").setTextPen(pg.mkPen(COLORS["muted"]))
        plot_item.getAxis("left").setTextPen(pg.mkPen(COLORS["muted"]))

        self._curve = plot_item.plot(
            pen=pg.mkPen(COLORS["cyan"], width=3),
            symbolBrush=COLORS["amber"],
            symbolPen=None,
            symbolSize=5,
        )
        layout.addWidget(plot)

    def set_series(self, x_values: list[float], y_values: list[float]) -> None:
        if self._curve is None:
            return
        self._curve.setData(x_values, y_values)
