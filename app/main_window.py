"""Main window: toolbar + a mode switcher + stacked editor panes."""
from __future__ import annotations

import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QToolBar,
    QMenu,
    QMessageBox,
    QComboBox,
    QStackedWidget,
    QFileDialog,
    QWidget,
    QVBoxLayout,
    QApplication,
    QSpinBox,
)
from PySide6.QtGui import QAction, QKeySequence, QIcon

from .config_model import ConfigModel
from .provider_panel import ProviderPanel
from .mcp_panel import MCPPanel
from .preview_panel import PreviewPanel, mask_secrets
from .misc_panels import AgentPanel, SkillPanel, PermissionPanel
from .global_panel import GlobalPanel
from .styles import (
    apply_theme,
    current_font_size,
    current_theme,
    load_recent,
    remember,
    settings,
)

# Pairs we know upstream schema rejects though config runs fine.
BENIGN_TYPES = (
    ("mcp/", "not valid under any of the given schemas"),  # env-vs-environment
    ("model", "' is not one of ['"),                      # models.dev enum (custom providers)
)


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigModel):
        super().__init__()
        self.config = config
        self.setWindowTitle("opencode.json Editor")
        self.setWindowIcon(QIcon("assets/opencode.ico"))
        self.resize(1280, 780)

        self._schema = None  # type: ignore
        self._dirty = False
        self._theme = current_theme()
        self._font_size = current_font_size()
        self._recent = load_recent()

        self._build_toolbar()
        self._build_body()
        self._build_shortcuts()
        self._restore_ui_state()
        self._apply_ui_settings()
        self._status("พร้อม")

    # ---- UI construction -------------------------------------------------

    def _build_toolbar(self) -> None:
        bar = QToolBar("หลัก")
        bar.setMovable(False)
        self.addToolBar(bar)

        for text, slot in [("เปิด", self.open_file), ("บันทึก", self.save),
                           ("โหลดซ้ำ", self.reload), ("บันทึกเป็น...", self.save_as)]:
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

        bar.addSeparator()

        act_copy = QAction("คัดลอก JSON", self)
        act_copy.triggered.connect(self.copy_json)
        bar.addAction(act_copy)

        bar.addSeparator()

        # theme + font size controls (applied globally, persisted in QSettings)
        act_theme = QAction("ธีม (Dark/Light)", self)
        act_theme.triggered.connect(self.toggle_theme)
        bar.addAction(act_theme)

        font_label = QLabel(" ฟอนต์:")
        bar.addWidget(font_label)
        self.font_spin = QSpinBox()
        self.font_spin.setRange(8, 24)
        self.font_spin.setValue(self._font_size)
        self.font_spin.setToolTip("ขนาดฟอนต์ทั้งแอป (จุด)")
        self.font_spin.valueChanged.connect(self.set_font_size)
        bar.addWidget(self.font_spin)

        bar.addSeparator()
        self._build_recent_menu(bar)

    def _build_recent_menu(self, bar: QToolBar) -> None:
        btn = QAction("เปิดล่าสุด", self)
        menu = QMenu(self)
        btn.setMenu(menu)
        bar.addAction(btn)
        self._recent_menu = menu
        self._refresh_recent_menu()

    def _refresh_recent_menu(self) -> None:
        self._recent_menu.clear()
        if not self._recent:
            a = self._recent_menu.addAction("(ว่าง)")
            a.setEnabled(False)
            return
        for path in self._recent:
            a = self._recent_menu.addAction(path)
            a.triggered.connect(lambda checked=False, p=path: self.open_recent(p))
        self._recent_menu.addSeparator()
        a = self._recent_menu.addAction("ล้างรายการ")
        a.triggered.connect(self.clear_recent)

    def open_recent(self, path: str) -> None:
        if not self._confirm_discard():
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "เปิดล่าสุด", f"ไฟล์ไม่พบ:\n{path}")
            self._recent = [p for p in self._recent if p != path]
            self._refresh_recent_menu()
            return
        self.load_from(path)

    def clear_recent(self) -> None:
        self._recent = []
        self._refresh_recent_menu()

    def _build_shortcuts(self) -> None:
        self._add_shortcut("Ctrl+O", self.open_file)
        self._add_shortcut("Ctrl+S", self.save)
        self._add_shortcut("Ctrl+Shift+S", self.save_as)
        self._add_shortcut("F5", self.reload)
        self._add_shortcut("Ctrl+Shift+V", self.validate)
        self._add_shortcut("Ctrl+Shift+C", self.copy_json)

    def _add_shortcut(self, seq: str, slot) -> None:
        act = QAction(self)
        act.setShortcut(QKeySequence(seq))
        act.triggered.connect(slot)
        self.addAction(act)

    def _restore_ui_state(self) -> None:
        s = settings()
        geo = s.value("window/geometry")
        if geo is not None:
            self.restoreGeometry(geo)

    def _apply_ui_settings(self) -> None:
        apply_theme(QApplication.instance() or QApplication([]), self._theme, self._font_size)

    def set_font_size(self, size: int) -> None:
        self._font_size = size
        apply_theme(QApplication.instance() or QApplication([]), self._theme, size)
        self._status(f"ฟอนต์ {size}pt")

    def toggle_theme(self) -> None:
        self._theme = "light" if self._theme == "dark" else "dark"
        apply_theme(QApplication.instance() or QApplication([]), self._theme, self._font_size)
        self._status(f"ธีม: {self._theme}")

    def _build_body(self) -> None:
        self.nav = ProviderPanel(self.config, self)
        self.mcp_tab = MCPPanel(self.config, self)
        self.agent_tab = AgentPanel(self.config, self)
        self.skill_tab = SkillPanel(self.config, self)
        self.perm_tab = PermissionPanel(self.config, self)
        self.global_tab = GlobalPanel(self.config, self)
        self.preview = PreviewPanel(self.config, self)

        self.stack = QStackedWidget()
        self.stack.addWidget(self.nav)
        self.stack.addWidget(self.mcp_tab)
        self.stack.addWidget(self.agent_tab)
        self.stack.addWidget(self.skill_tab)
        self.stack.addWidget(self.perm_tab)
        self.stack.addWidget(self.global_tab)
        self.stack.addWidget(self.preview)

        self.mode_sel = QComboBox()
        self.mode_sel.addItems(
            ["Provider / Model", "MCP Servers", "Agent", "Skill", "Permission",
             "Global", "JSON Preview"]
        )
        self.mode_sel.currentIndexChanged.connect(self.on_mode_changed)
        self.stack.currentChanged.connect(self.mode_sel.setCurrentIndex)

        wrapper = QWidget()
        outer = QVBoxLayout()
        outer.setContentsMargins(6, 6, 6, 6)
        outer.addWidget(self.mode_sel)
        outer.addWidget(self.stack)
        wrapper.setLayout(outer)

        self.setCentralWidget(wrapper)

        self.nav.data_changed.connect(self._on_data_changed)
        self.mcp_tab.data_changed.connect(self._on_data_changed)
        self.agent_tab.data_changed.connect(self._on_data_changed)
        self.skill_tab.data_changed.connect(self._on_data_changed)
        self.perm_tab.data_changed.connect(self._on_data_changed)
        self.global_tab.data_changed.connect(self._on_data_changed)

    # ---- actions ---------------------------------------------------------

    def on_mode_changed(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 6:
            # refresh preview with the latest committed data before showing it
            self._commit_all()
            self.preview.refresh()

    def _commit_all(self) -> None:
        self.mcp_tab.commit()
        self.nav.commit()
        self.agent_tab.commit()
        self.skill_tab.commit()
        self.perm_tab.commit()
        self.global_tab.commit()

    def open_file(self) -> None:
        if not self._confirm_discard():
            return
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
        self._dirty = False
        self.path_label.setText(path)
        self._update_title()
        self.nav.set_config(self.config)
        self.mcp_tab.set_config(self.config)
        self.agent_tab.set_config(self.config)
        self.skill_tab.set_config(self.config)
        self.perm_tab.set_config(self.config)
        self.global_tab.set_config(self.config)
        self.preview.set_config(self.config)
        self._status(f"เปิด {os.path.basename(path)} แล้ว")

    def reload(self) -> None:
        if not self._confirm_discard():
            return
        self.load_from(self.config.path)

    def save(self) -> None:
        self._commit_all()
        self.preview.refresh()
        try:
            self.config.save()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "บันทึกไม่สำเร็จ", str(exc))
            return
        self._dirty = False
        self._update_title()
        self._status(f"บันทึกแล้ว -> {self.config.path}")

    def save_as(self) -> None:
        self._commit_all()
        path, _ = QFileDialog.getSaveFileName(
            self, "บันทึกเป็น", self.config.path, "JSON (*.json *.jsonc)"
        )
        if not path:
            return
        self.config.path = path
        try:
            self.config.save()
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "บันทึกไม่สำเร็จ", str(exc))
            return
        self._dirty = False
        self.path_label.setText(path)
        self._update_title()
        self._status(f"บันทึกแล้ว -> {path}")

    def copy_json(self) -> None:
        self._commit_all()
        masked = mask_secrets(self.config.data)
        QApplication.clipboard().setText(json.dumps(masked, indent=2, ensure_ascii=False))
        self._status("คัดลอก JSON (apiKey ถูกปกปิด) ไปยังคลิปบอร์ดแล้ว")

    def validate(self) -> None:
        self._commit_all()
        schema = self._get_schema()
        if not schema:
            QMessageBox.warning(self, "ตรวจ Schema", "ดาวน์โหลด schema ไม่สำเร็จ (เช็คเน็ต)")
            return
        errors = self.config.schema_errors(schema)
        if not errors:
            QMessageBox.information(self, "ตรวจ Schema", "ผ่านทุกข้อ")
            return
        real, benign = [], []
        for e in errors:
            if any(k in e and m in e for k, m in BENIGN_TYPES):
                benign.append(e)
            else:
                real.append(e)
        lines = []
        lines.append(f"พบข้อผิดพลาด {len(errors)} จุด (สำคัญ {len(real)} / เป็น known-issue {len(benign)}):\n")
        lines += real[:20]
        if benign:
            lines.append("\n— ต่อไปนี้เป็นข้อจำกัดของ schema ทางการ (opencode รันได้จริง, แก้ไม่ได้ที่เรา):")
            lines += benign[:10]
        QMessageBox.warning(self, "ตรวจ Schema", "\n".join(lines))

    def _get_schema(self):
        # Cache only successful fetches: a failure must retry on the next click
        # instead of showing "download failed" forever.
        if self._schema is None or not self._schema:
            self._schema = ConfigModel.fetch_schema()
        return self._schema

    # ---- dirty tracking --------------------------------------------------

    def _on_data_changed(self) -> None:
        self._dirty = True
        self._update_title()
        self._status("มีการเปลี่ยนแปลง (ยังไม่บันทึก)")

    def _update_title(self) -> None:
        marker = " *" if self._dirty else ""
        base = os.path.basename(self.config.path) if self.config.path else "opencode.json"
        self.setWindowTitle(f"{base}{marker} — opencode.json Editor")

    def _confirm_discard(self) -> bool:
        """Ask before throwing away uncommitted edits. Returns True to proceed."""
        if not self._dirty:
            return True
        which = ["Provider/Model", "MCP", "Agent/Skill/Permission"]
        ans = QMessageBox.question(
            self, "ยังไม่ได้บันทึก",
            "มีข้อมูลที่ยังไม่ได้บันทึก — ต้องการทิ้งการแก้ไขและโหลดต่อหรือไม่?",
            QMessageBox.Yes | QMessageBox.No,
        )
        return ans == QMessageBox.Yes

    def closeEvent(self, event) -> None:
        if self._dirty:
            ans = QMessageBox.question(
                self, "ปิดโดยไม่บันทึก",
                "มีข้อมูลที่ยังไม่ได้บันทึก — ออกหรือไม่?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans != QMessageBox.Yes:
                event.ignore()
                return
        remember(self)
        event.accept()

    def _status(self, msg: str) -> None:
        self.statusBar().showMessage(msg, 8000)
