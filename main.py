"""Entry point for the opencode.json GUI editor.

Usage:
    python main.py [path/to/opencode.json]
"""
from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication, QMessageBox

from app.config_model import ConfigModel
from app.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("opencode-config-editor")

    from app.styles import apply_theme, current_font_size, current_theme

    apply_theme(app, current_theme(), current_font_size())

    path = sys.argv[1] if len(sys.argv) > 1 else ConfigModel.DEFAULT_CONFIG_PATH
    try:
        config = ConfigModel.load(path)
    except Exception as exc:  # noqa: BLE001
        # If the file is missing or unreadable, still open the editor with an
        # in-memory config so the user can create/recover it.
        QMessageBox.warning(None, "เปิด config ไม่สำเร็จ", f"{exc}\n\nเปิดหน้าต่างว่างแทน (บันทึกจะเขียนทับที่ path นี้)")
        config = ConfigModel(data={}, path=path)

    window = MainWindow(config)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
