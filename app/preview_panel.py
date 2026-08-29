"""Live JSON preview of the config under edit.

Shows the full config.data as pretty JSON, masking secrets (apiKey,
authorization headers) so the user can review everything that would be saved
without exposing credentials. UI-free side: masking lives here, not in the
data model, so ConfigModel keeps real values at all times.
"""
from __future__ import annotations

import copy
import json
from typing import Any

from PySide6.QtWidgets import (
    QVBoxLayout,
    QWidget,
)

from PySide6.QtGui import (
    QFontDatabase,
)

from PySide6.QtWidgets import QPlainTextEdit, QLabel

SECRET_KEYS = {"apiKey", "api_key", "apikey", "key", "token", "authorization", "password"}


def is_secret_value(value: str) -> bool:
    """Heuristic: values that look like embedded credentials."""
    v = value.strip()
    return v.lower().startswith(("bearer ", "basic ", "token ", "sk-", "apikey ")) or len(v) > 40


def mask_secrets(data: Any, path: tuple[str, ...] = ()) -> Any:
    """Return a deep copy with secret values replaced by '***'."""
    if isinstance(data, dict):
        out: dict[str, Any] = {}
        for k, v in data.items():
            if isinstance(k, str) and k in SECRET_KEYS and isinstance(v, str) and v:
                out[k] = "***"
            elif isinstance(k, str) and k.lower() in SECRET_KEYS and isinstance(v, str) and v:
                out[k] = "***"
            elif isinstance(v, str) and is_secret_value(v):
                out[k] = "***"
            else:
                out[k] = mask_secrets(v, path + (str(k),))
        return out
    if isinstance(data, list):
        return [mask_secrets(item, path) for item in data]
    return data


class PreviewPanel(QWidget):
    """Read-only pretty JSON view of the live config."""

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        self.hint = QLabel("อัปเดตสดหลังกดบันทึก/ตรวจ — สมาชิก apiKey/headers ถูกปกปิด (***)")
        self.hint.setStyleSheet("color:#888;")
        outer.addWidget(self.hint)

        self.text = QPlainTextEdit()
        self.text.setReadOnly(True)
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(10)
        self.text.setFont(font)
        self.text.setLineWrapMode(QPlainTextEdit.NoWrap)
        outer.addWidget(self.text)

        self.refresh()

    def set_config(self, config) -> None:
        self.config = config
        self.refresh()

    def refresh(self) -> None:
        """Re-render from config.data (session data stays unmasked safe)."""
        masked = mask_secrets(self.config.data)
        text = json.dumps(masked, indent=2, ensure_ascii=False)
        self.text.setPlainText(text)
