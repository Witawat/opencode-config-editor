"""Smoke test: load the real config, build the GUI (offscreen), round-trip save
without corrupting the existing file. Run with: python test_smoke.py

This does not modify the config file in a meaningful way if the user did not
change anything -- but it WILL rewrite it with indent=2. Use on a copy if you
want to be safe.
"""
from __future__ import annotations

import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from app.config_model import ConfigModel
from app.main_window import MainWindow


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else ConfigModel.DEFAULT_CONFIG_PATH
    print(f"[1] load {path}")
    config = ConfigModel.load(path)
    print(f"    providers={len(config.providers)} mcp={len(config.mcp)}")

    print("[2] build GUI")
    app = QApplication.instance() or QApplication([])
    window = MainWindow(config)
    window.show()
    QTimer.singleShot(50, app.quit)
    app.exec()
    print("    GUI ok")

    print("[3] commit + save round-trip")
    window.nav.commit()
    window.mcp_tab.commit()
    config.save()
    print("    saved")

    print("[4] reload and compare keys")
    reloaded = ConfigModel.load(path)
    assert reloaded.providers.keys() == config.providers.keys(), "providers differ"
    assert reloaded.mcp.keys() == config.mcp.keys(), "mcp differ"
    print("    OK: keys preserved")

    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
