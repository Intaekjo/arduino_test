from __future__ import annotations

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication


COLORS = {
    "bg": "#07101b",
    "panel": "#0d1b29",
    "panel_alt": "#102235",
    "cyan": "#57e3ff",
    "cyan_dim": "#1c7fa0",
    "amber": "#ffb65c",
    "amber_soft": "#f5d0a0",
    "danger": "#ff5d5d",
    "text": "#d9f6ff",
    "muted": "#7ca4b8",
}


def apply_hud_theme(app: QApplication) -> None:
    font = QFont("Bahnschrift SemiCondensed", 10)
    app.setFont(font)

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["panel"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["panel_alt"]))
    palette.setColor(QPalette.Text, QColor(COLORS["text"]))
    palette.setColor(QPalette.Button, QColor(COLORS["panel_alt"]))
    palette.setColor(QPalette.ButtonText, QColor(COLORS["text"]))
    app.setPalette(palette)
    app.setStyleSheet(build_stylesheet())


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        background: {COLORS["bg"]};
        color: {COLORS["text"]};
    }}
    QWidget[hudPanel="true"] {{
        background: {COLORS["panel"]};
        border: 1px solid {COLORS["cyan_dim"]};
        border-radius: 18px;
    }}
    QLabel[panelTitle="true"] {{
        color: {COLORS["cyan"]};
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
    }}
    QLabel[muted="true"] {{
        color: {COLORS["muted"]};
    }}
    QComboBox, QPushButton, QPlainTextEdit {{
        border-radius: 12px;
        border: 1px solid {COLORS["cyan_dim"]};
        padding: 8px 12px;
        background: {COLORS["panel_alt"]};
        color: {COLORS["text"]};
    }}
    QComboBox:hover, QPushButton:hover {{
        border-color: {COLORS["cyan"]};
    }}
    QComboBox::drop-down {{
        border: none;
        width: 28px;
    }}
    QPushButton {{
        font-weight: 700;
        letter-spacing: 1px;
    }}
    QPushButton:disabled {{
        color: #6a8591;
        border-color: #274050;
    }}
    QPushButton[accent="true"] {{
        background: #113447;
    }}
    QPushButton[danger="true"] {{
        background: #431f28;
        border-color: #a1465d;
    }}
    QPushButton[solenoid="true"] {{
        min-height: 56px;
        font-size: 16px;
    }}
    QPushButton[solenoid="true"]:checked {{
        background: #4b241d;
        border-color: {COLORS["amber"]};
        color: {COLORS["amber_soft"]};
    }}
    QPlainTextEdit {{
        background: #08131e;
        font-family: Consolas;
        selection-background-color: {COLORS["cyan_dim"]};
    }}
    """
