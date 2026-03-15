from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from .constants import APP_NAME
from .main_window import MainWindow
from .ui_theme import apply_hud_theme


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    apply_hud_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())

