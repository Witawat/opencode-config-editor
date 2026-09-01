"""Theme + font management (QSS / QApplication).

Provides two built-in QSS themes (dark/light), applying them plus a user font
size. Settings (theme, font size, window geometry, last path, recent files)
live in QSettings -- small and dependency-free.
"""
from __future__ import annotations

from PySide6.QtCore import QSettings
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from .config_model import DEFAULT_CONFIG_PATH

ORG = "opencode-config-editor"
APP = "opencode-config-editor"


def settings() -> QSettings:
    return QSettings(ORG, APP)


DEFAULT_THEME = "dark"
DEFAULT_FONT_SIZE = 12

LIGHT_QSS = """
QWidget { background: #f5f6f8; color: #20242a; }
QToolBar { background: #eceef1; border: none; padding: 4px; }
QStatusBar { background: #eceef1; color: #555; }
QListWidget, QTreeWidget, QPlainTextEdit, QTextEdit { background: #ffffff; border: 1px solid #c9ccd1; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #ffffff; border: 1px solid #c9ccd1; }
QPushButton { background: #ffffff; border: 1px solid #c0c3c8; padding: 4px 10px; }
QPushButton:hover { background: #e8eaee; }
QCheckBox { spacing: 6px; }
"""

DARK_QSS = """
QWidget { background: #1e1f24; color: #e6e8ec; }
QToolBar { background: #26272d; border: none; padding: 4px; }
QStatusBar { background: #26272d; color: #9aa0a8; }
QListWidget, QTreeWidget { background: #26272d; alternate-background-color: #2b2c33; }
QPlainTextEdit, QTextEdit { background: #17181c; color: #dfe3e8; border: 1px solid #3a3c44; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox { background: #26272d; border: 1px solid #3a3c44; color: #e6e8ec;
    selection-background-color: #3b6ea5; }
QComboBox QAbstractItemView { background: #26272d; }
QPushButton { background: #2e3038; border: 1px solid #44464f; padding: 4px 10px; }
QPushButton:hover { background: #383a44; }
QCheckBox { spacing: 6px; }
QLabel { background: transparent; }
QGroupBox { border: 1px solid #33353d; margin-top: 8px; padding-top: 6px; }
QGroupBox::title { subcontrol-origin: margin; left: 8px; padding: 0 4px; }
QToolTip { background: #2e3038; color: #e6e8ec; border: 1px solid #44464f; }
QScrollBar { background: transparent; }
QScrollBar:vertical { width: 12px; margin: 0; }
QScrollBar::handle:vertical { background: #4a4d57; border-radius: 6px; min-height: 24px; }
QScrollBar:horizontal { height: 12px; margin: 0; }
QScrollBar::handle:horizontal { background: #4a4d57; border-radius: 6px; min-width: 24px; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QHeaderView::section { background: #2b2c33; border: none; padding: 4px; }
"""


def apply_theme(app: QApplication, theme: str, font_size: int) -> None:
    """Apply theme QSS + a global font size to the application."""
    qss = DARK_QSS if theme == "dark" else LIGHT_QSS
    app.setStyleSheet(qss)
    font = QFont()
    font.setPointSize(max(8, min(24, int(font_size))))
    app.setFont(font)


def current_font_size() -> int:
    s = settings()
    ff = s.value("ui/font_size", DEFAULT_FONT_SIZE, type=int)
    try:
        return int(ff) if ff else DEFAULT_FONT_SIZE
    except (TypeError, ValueError):
        return DEFAULT_FONT_SIZE


def current_theme() -> str:
    s = settings()
    v = s.value("ui/theme", DEFAULT_THEME)
    return v if v in ("dark", "light") else DEFAULT_THEME


def system_is_dark() -> bool:
    """Detect the OS theme via the default QApplication palette."""
    app = QApplication.instance()
    if app is None:
        return False
    from PySide6.QtGui import QPalette

    win = app.palette().color(QPalette.Window)
    # A light window color is "brighter" than dark; compare luminance.
    lum = 0.299 * win.red() + 0.587 * win.green() + 0.114 * win.blue()
    return lum < 128


def effective_theme() -> str:
    """theme from settings, or follow system when set to 'auto'."""
    s = settings()
    v = s.value("ui/theme", "auto")
    if v in ("dark", "light"):
        return v
    return "dark" if system_is_dark() else "light"


def remember(window) -> None:
    """Persist UI state after a successful session."""
    s = settings()
    s.setValue("ui/font_size", current_font_size())
    s.setValue("ui/theme", current_theme())
    s.setValue("window/geometry", window.saveGeometry())
    s.setValue("window/state", window.saveState())
    s.setValue("last/path", getattr(window.config, "path", DEFAULT_CONFIG_PATH))
    # recent files
    recent = getattr(window, "_recent", []) or []
    cur = getattr(window.config, "path", "")
    if cur and cur not in recent:
        recent = [cur] + recent
    recent = [r for r in recent if r][:5]
    window._recent = recent
    s.setValue("recent/files", recent)
    s.sync()


def load_recent() -> list[str]:
    s = settings()
    recent = s.value("recent/files", [], type=list)
    return [r for r in recent if isinstance(r, str) and r][:5]
