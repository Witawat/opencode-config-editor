"""Main window: toolbar + a mode switcher + stacked editor panes."""
from __future__ import annotations

import os

from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QToolBar,
    QMessageBox,
    QComboBox,
    QStackedWidget,
    QFileDialog,
    QWidget,
    QVBoxLayout,
)
from PySide6.QtGui import QAction

from .config_model import ConfigModel
from .provider_panel import ProviderPanel
from .mcp_panel import MCPPanel


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigModel):
        super().__init__()
        self.config = config
        self.setWindowTitle("opencode.json Editor")
        self.resize(1280, 780)

        self._schema = None  # type: ignore

        self._build_toolbar()
        self._build_body()
        self._status("พร้อม")

    # ---- UI construction -------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = QToolBar("หลัก")
        bar.setMovable(False)
        self.addToolBar(bar)

        for text, slot in [("เปิด", self.open_file), ("บันทึก", self.save), ("โหลดซ้ำ", self.reload)]:
            act = QAction(text, self)
            act.triggered.connect(slot)
            bar.addAction(act)

        bar.addSeparator()

        self.path_label = QLabel(self.config.path)
        self.path_label.setStyleSheet("color:#888; padding-left:8px;")
        bar.addWidget(self.path_label)

        bar.addSeparator()

        act_validate = QAction("ตรวจ Schema", self)
        act_validate.triggered.connect(self.validate)
        bar.addAction(act_validate)

    def _build_body(self) -> None:
        self.nav = ProviderPanel(self.config, self)
        self.mcp_tab = MCPPanel(self.config, self)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.nav)
        self.stack.addWidget(self.mcp_tab)

        self.mode_sel = QComboBox()
        self.mode_sel.addItems(["Provider / Model", "MCP Servers"])
        self.mode_sel.currentIndexChanged.connect(self.stack.setCurrentIndex)
        self.stack.currentChanged.connect(self.mode_sel.setCurrentIndex)

        wrapper = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(6, 6, 6, 6)
        outer.addWidget(self.mode_sel)
        outer.addWidget(self.stack)
        wrapper.setLayout(outer)

        self.setCentralWidget(wrapper)

        self.nav.data_changed.connect(lambda: self._status("มีการเปลี่ยนแปลง (ยังไม่บันทึก)"))

    # ---- actions ---------------------------------------------------------

    def open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "เปิด opencode.json", self.config.path, "JSON (*.json *.jsonc)"
        )
        if not path:
            return
        self.load_from(path)

    def load_from(self, path: str) -> None:
        try:
            self.config = ConfigModel.load(path)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "โหลดไม่สำเร็จ", str(exc))
            return
        self.path_label.setText(path)
        self.nav.set_config(self.config)
        self.mcp_tab.set_config(self.config)
        self._status(f"เปิด {os.path.basename(path)} แล้ว")

    def reload(self) -> None:
        self.load_from(self.config.path)

    def save(self) -> None:
        self.nav.commit()
        self.mcp_tab.commit()
        try:
            self.config.save()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "บันทึกไม่สำเร็จ", str(exc))
            return
        self._status(f"บันทึกแล้ว -> {self.config.path}")

    def validate(self) -> None:
        self.nav.commit()
        schema = self._get_schema()
        if not schema:
            QMessageBox.warning(self, "ตรวจ Schema", "ดาวน์โหลด schema ไม่สำเร็จ (เช็คเน็ต)")
            return
        errors = self.config.schema_errors(schema)
        if errors:
            QMessageBox.warning(self, "พบปัญหา", f"พบข้อผิดพลาด {len(errors)} จุด:\n\n" + "\n".join(errors[:20]))
        else:
            QMessageBox.information(self, "ตรวจ Schema", "ผ่านทุกข้อ")

    def _get_schema(self):
        if self._schema is None:
            self._schema = ConfigModel.fetch_schema()
        return self._schema

    def _status(self, msg: str) -> None:
        self.statusBar().showMessage(msg, 8000)
