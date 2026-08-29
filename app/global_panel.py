"""Global / top-level config editing: model, small_model, instructions,
compaction, enabled_providers (whitelist), disabled_providers (blacklist).

One form for everything that used to be invisible in the editor. Unknown keys
are merge-preserved like the rest of the app.
"""
from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QListWidget,
    QSpinBox,
    QInputDialog,
    QScrollArea,
    QGroupBox,
)


class GlobalPanel(QWidget):
    data_changed = Signal()

    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config

        outer = QVBoxLayout(self)
        outer.setContentsMargins(4, 4, 4, 4)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        form = QFormLayout(inner)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        self.f_model = QLineEdit()
        self.f_model.setPlaceholderText("provider/model เช่น anthropic/claude-2")
        form.addRow("model", self.f_model)

        self.f_small_model = QLineEdit()
        self.f_small_model.setPlaceholderText("สำหรับ tasks เล็ก เช่น title")
        form.addRow("small_model", self.f_small_model)

        # instructions
        instr_box = QGroupBox("instructions (ไฟล์คำสั่ง)")
        i_layout = QVBoxLayout(instr_box)
        i_btns = QHBoxLayout()
        b_add = QPushButton("+ เพิ่ม")
        b_add.clicked.connect(self.add_instruction)
        b_del = QPushButton("ลบเส้น")
        b_del.clicked.connect(self.del_instruction)
        i_btns.addWidget(b_add)
        i_btns.addWidget(b_del)
        i_btns.addStretch()
        self.instructions_list = QListWidget()
        self.instructions_list.setMaximumHeight(120)
        i_layout.addLayout(i_btns)
        i_layout.addWidget(self.instructions_list)
        form.addRow(instr_box)

        # whitelist / blacklist of providers
        prov_box = QGroupBox("whitelist / blacklist ของ provider (top-level)")
        p_layout = QVBoxLayout(prov_box)

        self.enabled_list = QListWidget()
        self.enabled_list.setMaximumHeight(110)
        self.disabled_list = QListWidget()
        self.disabled_list.setMaximumHeight(110)
        self.p_enabled = _LineList("enabled_providers (whitelist) — เมื่อตั้งแล้วใช้แค่นี้",
                                   self.add_enabled, self.del_enabled, self.enabled_list)
        self.p_disabled = _LineList("disabled_providers (blacklist) — ปิด provider ที่โหลดอัตโนมัติ",
                                    self.add_disabled, self.del_disabled, self.disabled_list)
        p_layout.addWidget(self.p_enabled)
        p_layout.addWidget(self.p_disabled)
        form.addRow(prov_box)

        # compaction
        comp_box = QGroupBox("compaction (บีบข้อมูลเมื่อ context เต็ม)")
        c_form = QFormLayout(comp_box)
        self.c_auto = QCheckBox("auto")
        self.c_prune = QCheckBox("prune")
        c_form.addRow("", self.c_auto)
        c_form.addRow("", self.c_prune)
        self._comp_touched: set[str] = set()
        self.c_auto.stateChanged.connect(lambda _: self._comp_touched.add("auto"))
        self.c_prune.stateChanged.connect(lambda _: self._comp_touched.add("prune"))
        self.c_tail_turns = QSpinBox()
        self.c_tail_turns.setRange(0, 10_000_000)
        self.c_preserve = QSpinBox()
        self.c_preserve.setRange(0, 10_000_000)
        self.c_preserve.setSuffix(" tokens")
        self.c_reserved = QSpinBox()
        self.c_reserved.setRange(0, 10_000_000)
        self.c_reserved.setSuffix(" tokens")
        c_form.addRow("tail_turns", self.c_tail_turns)
        c_form.addRow("preserve_recent_tokens", self.c_preserve)
        c_form.addRow("reserved", self.c_reserved)
        form.addRow(comp_box)

        scroll.setWidget(inner)
        outer.addWidget(scroll)

        self._populate()

    def set_config(self, config) -> None:
        self.config = config
        self._populate()

    # ---- list helpers ------------------------------------------------------

    def _populate(self) -> None:
        d = self.config.data
        self.f_model.setText(str(d.get("model", "")))
        self.f_small_model.setText(str(d.get("small_model", "")))

        self.instructions_list.clear()
        for p in [p for p in d.get("instructions", []) or [] if isinstance(p, str)]:
            self.instructions_list.addItem(p)

        self.enabled_list.clear()
        for p in [p for p in d.get("enabled_providers", []) or [] if isinstance(p, str)]:
            self.enabled_list.addItem(p)

        self.disabled_list.clear()
        for p in [p for p in d.get("disabled_providers", []) or [] if isinstance(p, str)]:
            self.disabled_list.addItem(p)

        comp = d.get("compaction") or {}
        if not isinstance(comp, dict):
            comp = {}
        self.c_auto.setChecked(bool(comp.get("auto", True)))
        self.c_prune.setChecked(bool(comp.get("prune", False)))
        self.c_tail_turns.setValue(int(comp.get("tail_turns", 0) or 0))
        self.c_preserve.setValue(int(comp.get("preserve_recent_tokens", 0) or 0))
        self.c_reserved.setValue(int(comp.get("reserved", 0) or 0))
        # setValue/setChecked above fire signals; drop synthetic events so only
        # real user edits count (mirror of provider cost spinbox handling).
        self._comp_touched.clear()

    def add_instruction(self) -> None:
        val, ok = QInputDialog.getText(self, "เพิ่ม instruction", "path ของไฟล์ instruction:")
        if not ok or not val.strip():
            return
        d = self.config.data
        d.setdefault("instructions", []).append(val.strip())
        self.instructions_list.addItem(val.strip())
        self.data_changed.emit()

    def del_instruction(self) -> None:
        row = self.instructions_list.currentRow()
        if row < 0:
            return
        self.config.data.setdefault("instructions", []).pop(row)
        self.instructions_list.takeItem(row)
        self.data_changed.emit()

    def add_enabled(self) -> None:
        val, ok = QInputDialog.getText(self, "เพิ่ม whitelist", "ชื่อ provider (whitelist):")
        if not ok or not val.strip():
            return
        self.config.data.setdefault("enabled_providers", []).append(val.strip())
        self.enabled_list.addItem(val.strip())
        self.data_changed.emit()

    def del_enabled(self) -> None:
        row = self.enabled_list.currentRow()
        if row < 0:
            return
        self.config.data.setdefault("enabled_providers", []).pop(row)
        self.enabled_list.takeItem(row)
        self.data_changed.emit()

    def add_disabled(self) -> None:
        val, ok = QInputDialog.getText(self, "เพิ่ม blacklist", "ชื่อ provider (blacklist):")
        if not ok or not val.strip():
            return
        self.config.data.setdefault("disabled_providers", []).append(val.strip())
        self.disabled_list.addItem(val.strip())
        self.data_changed.emit()

    def del_disabled(self) -> None:
        row = self.disabled_list.currentRow()
        if row < 0:
            return
        self.config.data.setdefault("disabled_providers", []).pop(row)
        self.disabled_list.takeItem(row)
        self.data_changed.emit()

    def commit(self) -> None:
        """Write form values into config.data (merge style)."""
        d = self.config.data
        if self.f_model.text():
            d["model"] = self.f_model.text()
        else:
            d.pop("model", None)
        if self.f_small_model.text():
            d["small_model"] = self.f_small_model.text()
        else:
            d.pop("small_model", None)

        # compaction: boolean keys are written only when the user actually
        # toggled them (unchecking pops the key). Numbers keep 0-when-absent.
        comp: dict = {}
        touched_bools = [k for k in ("auto", "prune") if k in self._comp_touched]
        for key in touched_bools:
            if getattr(self, f"c_{key}").isChecked():
                comp[key] = True
        for val, key in [(self.c_tail_turns.value(), "tail_turns"),
                         (self.c_preserve.value(), "preserve_recent_tokens"),
                         (self.c_reserved.value(), "reserved")]:
            if val:
                comp[key] = val
        existing = d.get("compaction")
        if isinstance(existing, dict):
            if comp or touched_bools:
                for k in list(comp):
                    existing.pop(k, None)
                existing.update(comp)
                for k in touched_bools:
                    if k not in comp:
                        existing.pop(k, None)
                d["compaction"] = existing
            else:
                for k in ("auto", "prune", "tail_turns", "preserve_recent_tokens", "reserved"):
                    if k in self._comp_touched:
                        existing.pop(k, None)
                if not existing:
                    del d["compaction"]
                else:
                    d["compaction"] = existing
        elif comp:
            d["compaction"] = comp


class _LineList(QWidget):
    """A small vertical widget: label + list + add/del buttons."""

    def __init__(self, title: str, add_fn, del_fn, list_widget):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(QLabel(title))
        btns = QHBoxLayout()
        b_add = QPushButton("+ เพิ่ม")
        b_add.clicked.connect(add_fn)
        b_del = QPushButton("ลบเส้น")
        b_del.clicked.connect(del_fn)
        btns.addWidget(b_add)
        btns.addWidget(b_del)
        btns.addStretch()
        lay.addLayout(btns)
        lay.addWidget(list_widget)
