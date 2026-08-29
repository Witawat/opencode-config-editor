"""MCP servers editing: list on the left, editor form on the right."""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QStackedWidget,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTextEdit,
    QLabel,
    QMessageBox,
)

from .config_model import ConfigModel


class MCPPanel(QWidget):
    data_changed = Signal()

    def __init__(self, config: ConfigModel, parent=None):
        super().__init__(parent)
        self.config = config
        self._selected = None
        self._env_key = "environment"
        self._build_ui()
        self._populate()

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        left.addWidget(self.list)

        btns = QHBoxLayout()
        b_add = QPushButton("+ เพิ่ม")
        b_add.clicked.connect(self.add_server)
        b_del = QPushButton("ลบ")
        b_del.clicked.connect(self.delete_server)
        btns.addWidget(b_add)
        btns.addWidget(b_del)
        left.addLayout(btns)

        lw = QWidget()
        lw.setLayout(left)
        lw.setMaximumWidth(280)

        self.form = QWidget()
        form = QFormLayout(self.form)

        self.f_name_label = QLabel("")
        form.addRow("ชื่อ", self.f_name_label)

        self.f_type = QComboBox()
        self.f_type.addItems(["local", "remote"])
        form.addRow("type", self.f_type)

        self.f_enabled = QCheckBox("enabled")
        form.addRow("", self.f_enabled)

        self.f_command = QLineEdit()
        self.f_command.setPlaceholderText('เช่น: npx  -y  @playwright/mcp@latest   (คำสั่ง+args คั่นด้วยช่องว่าง)')
        form.addRow("command / url", self.f_command)

        self.f_url = QLineEdit()
        self.f_url.setPlaceholderText("remote URL (เฉพาะ type=remote)")
        form.addRow("url", self.f_url)

        self.f_headers = QTextEdit()
        self.f_headers.setPlaceholderText('JSON headers เช่น {"Authorization": "Bearer ..."}\n\nใช้ {env:VAR} ได้')
        form.addRow("headers", self.f_headers)

        self.f_env = QTextEdit()
        self.f_env.setPlaceholderText("JSON environment (สำหรับ local)")
        form.addRow("environment", self.f_env)

        root.addWidget(lw)
        root.addWidget(self.form, stretch=1)

    def set_config(self, config: ConfigModel) -> None:
        self.config = config
        self._populate()

    def _populate(self) -> None:
        self._building = True
        self.list.clear()
        self._selected = None
        for name, srv in self.config.mcp.items():
            state = "enabled" if srv.get("enabled", True) else "disabled"
            it = QListWidgetItem(f"{name}  [{srv.get('type', '?'):6s} · {state}]")
            it.setData(Qt.UserRole, name)
            self.list.addItem(it)
        self.list.setCurrentRow(-1)
        self._building = False
        self._clear_form()

    def _clear_form(self) -> None:
        self.f_name_label.setText("(ไม่เลือก)")
        self.f_type.setCurrentIndex(0)
        self.f_enabled.setChecked(True)
        self.f_command.clear()
        self.f_url.clear()
        self.f_headers.clear()
        self.f_env.clear()

    def _on_select(self, cur, prev) -> None:
        if self._building or cur is None:
            return
        self._selected = cur.data(Qt.UserRole)
        srv = self.config.mcp.get(self._selected, {})
        # opencode configs in the wild use either "env" or "environment"; preserve
        # whichever key is present.
        self._env_key = "environment" if "environment" in srv else "env"
        env = srv.get("environment", srv.get("env", {}))
        self.f_name_label.setText(self._selected)
        t = srv.get("type", "local")
        self.f_type.setCurrentText(t)
        self.f_enabled.setChecked(bool(srv.get("enabled", True)))
        if t == "local":
            self.f_command.setText(" ".join(srv.get("command", [])))
            self.f_env.setPlainText(json.dumps(env, ensure_ascii=False, indent=2) if env else "")
        else:
            self.f_command.clear()
            self.f_env.clear()
        self.f_url.setText(str(srv.get("url", "")))
        self.f_headers.setPlainText(json.dumps(srv.get("headers", {}), ensure_ascii=False, indent=2) if srv.get("headers") else "")

    def add_server(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "เพิ่ม MCP", "ชื่อ server:")
        if not ok or not name.strip():
            return
        name = name.strip()
        self.config.mcp.setdefault(name, {"type": "local", "enabled": True})
        self._populate()
        self._select(name)
        self.data_changed.emit()

    def delete_server(self) -> None:
        if not self._selected:
            return
        if QMessageBox.question(self, "ลบ", f"ลบ mcp '{self._selected}'?") == QMessageBox.Yes:
            self.config.mcp.pop(self._selected, None)
            self._populate()
            self.data_changed.emit()

    def _select(self, name: str) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.data(Qt.UserRole) == name:
                self.list.setCurrentRow(i)
                return

    def commit(self) -> None:
        if not self._selected:
            return
        srv = self.config.mcp.setdefault(self._selected, {})
        srv["type"] = self.f_type.currentText()
        srv["enabled"] = self.f_enabled.isChecked()
        t = self.f_type.currentText()
        if t == "local":
            args = [a for a in self.f_command.text().split() if a]
            if args:
                srv["command"] = args
            else:
                srv.pop("command", None)
            envtxt = self.f_env.toPlainText().strip()
            if envtxt:
                try:
                    envobj = json.loads(envtxt)
                except json.JSONDecodeError:
                    QMessageBox.warning(self, "environment ไม่ใช่ JSON", "ไม่บันทึก environment")
                    envobj = None
                if envobj is not None:
                    srv.pop("environment", None)
                    srv.pop("env", None)
                    srv[self._env_key] = envobj
            else:
                srv.pop("environment", None)
                srv.pop("env", None)
            srv.pop("url", None)
            srv.pop("headers", None)
        else:
            if self.f_url.text():
                srv["url"] = self.f_url.text()
                srv.setdefault("headers", {})
                htxt = self.f_headers.toPlainText().strip()
                if htxt:
                    try:
                        srv["headers"] = json.loads(htxt)
                    except json.JSONDecodeError:
                        QMessageBox.warning(self, "headers ไม่ใช่ JSON", "ไม่บันทึก headers")
                else:
                    srv.pop("headers", None)
            else:
                srv.pop("url", None)
                srv.pop("headers", None)
            srv.pop("command", None)
            srv.pop("environment", None)
