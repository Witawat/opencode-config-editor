"""Agent / Skill / Permission editing panels.

opencode.json supports (per config.json schema):
  agent       -> object keyed by agent name, each = AgentConfig
  skills      -> { paths: [...], urls: [...] }
  permission  -> { toolName: rule }

These panels follow the same pattern as MCPPanel: a left selector + a form
on the right. Commits merge, never rebuild, so unknown future keys survive.
"""
from __future__ import annotations

import json

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QListWidget,
    QListWidgetItem,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QTextEdit,
    QLabel,
    QMessageBox,
    QInputDialog,
    QDoubleSpinBox,
    QSpinBox,
)

from .config_model import ConfigModel

PERMISSION_TOOLS = [
    "read", "edit", "glob", "grep", "list", "bash", "task",
    "external_directory", "todowrite", "question", "webfetch",
    "websearch", "lsp", "doom_loop", "skill",
]

PERMISSION_MODES = ["ask", "allow", "deny"]


class AgentPanel(QWidget):
    data_changed = Signal()

    def __init__(self, config: ConfigModel, parent=None):
        super().__init__(parent)
        self.config = config
        self._selected = None
        self._building = False

        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        left.addWidget(self.list)

        btns = QHBoxLayout()
        b_add = QPushButton("+ เพิ่ม")
        b_add.clicked.connect(self.add_agent)
        b_del = QPushButton("ลบ")
        b_del.clicked.connect(self.delete_agent)
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

        self.f_model = QLineEdit()
        self.f_model.setPlaceholderText("provider/model")
        form.addRow("model", self.f_model)

        self.f_mode = QComboBox()
        self.f_mode.addItems(["subagent", "primary", "all"])
        form.addRow("mode", self.f_mode)

        self.f_color = QLineEdit()
        self.f_color.setPlaceholderText("#FF5733 หรือ primary/secondary/...")
        form.addRow("color", self.f_color)

        self.f_disable = QCheckBox("disable")
        self.f_hidden = QCheckBox("hidden")
        form.addRow("", self.f_disable)
        form.addRow("", self.f_hidden)

        self.f_temperature = QDoubleSpinBox()
        self.f_temperature.setRange(0, 2)
        self.f_temperature.setDecimals(2)
        self.f_temperature.setSingleStep(0.1)
        form.addRow("temperature", self.f_temperature)

        self.f_top_p = QDoubleSpinBox()
        self.f_top_p.setRange(0, 1)
        self.f_top_p.setDecimals(2)
        self.f_top_p.setSingleStep(0.05)
        form.addRow("top_p", self.f_top_p)

        self.f_steps = QSpinBox()
        self.f_steps.setRange(0, 10000)
        form.addRow("steps", self.f_steps)

        self.f_description = QTextEdit()
        self.f_description.setPlaceholderText("คำอธิบายเมื่อใช้ agent นี้")
        self.f_description.setMaximumHeight(70)
        form.addRow("description", self.f_description)

        self.f_prompt = QTextEdit()
        self.f_prompt.setPlaceholderText("system prompt ของ agent นี้")
        form.addRow("prompt", self.f_prompt)

        root.addWidget(lw)
        root.addWidget(self.form, stretch=1)

        self._populate()

    def set_config(self, config: ConfigModel) -> None:
        self.config = config
        self._populate()

    def _agents(self) -> dict:
        agents = self.config.data.get("agent")
        if isinstance(agents, dict):
            return agents
        return {}

    def _populate(self) -> None:
        self._building = True
        self.list.clear()
        self._selected = None
        for name in self._agents().keys():
            it = QListWidgetItem(name)
            it.setData(Qt.UserRole, name)
            self.list.addItem(it)
        self.list.setCurrentRow(-1)
        self._building = False
        self._clear_form()

    def _clear_form(self) -> None:
        self.f_name_label.setText("(ไม่เลือก)")
        self.f_model.clear()
        self.f_mode.setCurrentText("subagent")
        self.f_color.clear()
        self.f_disable.setChecked(False)
        self.f_hidden.setChecked(False)
        self.f_temperature.setValue(0.0)
        self.f_top_p.setValue(0.0)
        self.f_steps.setValue(0)
        self.f_description.clear()
        self.f_prompt.clear()

    def _on_select(self, cur, prev) -> None:
        if self._building or cur is None:
            return
        self._selected = cur.data(Qt.UserRole)
        a = self._agents().get(self._selected, {})
        self.f_name_label.setText(self._selected)
        self.f_model.setText(str(a.get("model", "")))
        self.f_mode.setCurrentText(str(a.get("mode", "subagent")))
        self.f_color.setText(str(a.get("color", "")))
        self.f_disable.setChecked(bool(a.get("disable", False)))
        self.f_hidden.setChecked(bool(a.get("hidden", False)))
        self.f_temperature.setValue(float(a.get("temperature", 0) or 0))
        self.f_top_p.setValue(float(a.get("top_p", 0) or 0))
        self.f_steps.setValue(int(a.get("steps", 0) or 0))
        self.f_description.setPlainText(str(a.get("description", "")))
        self.f_prompt.setPlainText(str(a.get("prompt", "")))

    def add_agent(self) -> None:
        name, ok = QInputDialog.getText(self, "เพิ่ม Agent", "ชื่อ agent:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if "agent" not in self.config.data or not isinstance(self.config.data["agent"], dict):
            self.config.data["agent"] = {}
        self.config.data["agent"].setdefault(name, {})
        self._populate()
        self._select(name)
        self.data_changed.emit()

    def delete_agent(self) -> None:
        if not self._selected:
            return
        if QMessageBox.question(self, "ลบ", f"ลบ agent '{self._selected}'?") == QMessageBox.Yes:
            self.config.data.get("agent", {}).pop(self._selected, None)
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
        if "agent" not in self.config.data or not isinstance(self.config.data["agent"], dict):
            return
        a = self.config.data["agent"].setdefault(self._selected, {})
        if self.f_model.text():
            a["model"] = self.f_model.text()
        else:
            a.pop("model", None)
        if self.f_mode.currentText():
            a["mode"] = self.f_mode.currentText()
        else:
            a.pop("mode", None)
        if self.f_color.text():
            a["color"] = self.f_color.text()
        else:
            a.pop("color", None)
        a["disable"] = self.f_disable.isChecked()
        a["hidden"] = self.f_hidden.isChecked()
        tmp = {}
        if self.f_temperature.value():
            tmp["temperature"] = self.f_temperature.value()
        if self.f_top_p.value():
            tmp["top_p"] = self.f_top_p.value()
        if self.f_steps.value():
            tmp["steps"] = self.f_steps.value()
        for k, v in tmp.items():
            a[k] = v
        if self.f_description.toPlainText().strip():
            a["description"] = self.f_description.toPlainText().strip()
        else:
            a.pop("description", None)
        if self.f_prompt.toPlainText().strip():
            a["prompt"] = self.f_prompt.toPlainText().strip()
        else:
            a.pop("prompt", None)


class SkillPanel(QWidget):
    """Edits skills.paths and skills.urls as simple line lists."""

    data_changed = Signal()

    def __init__(self, config: ConfigModel, parent=None):
        super().__init__(parent)
        self.config = config

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)

        # paths section
        p_box = QHBoxLayout()
        p_label = QLabel("skills.paths (โฟลเดอร์ skill)")
        p_box.addWidget(p_label, stretch=1)
        p_add = QPushButton("+ path")
        p_add.clicked.connect(self.add_path)
        p_del = QPushButton("ลบเส้น")
        p_del.clicked.connect(self.del_path)
        p_box.addWidget(p_add)
        p_box.addWidget(p_del)
        root.addLayout(p_box)

        self.paths_list = QListWidget()
        self.paths_list.setMinimumHeight(140)
        root.addWidget(self.paths_list)

        # urls section
        u_box = QHBoxLayout()
        u_label = QLabel("skills.urls (URL ที่จะดึง skill)")
        u_box.addWidget(u_label, stretch=1)
        u_add = QPushButton("+ url")
        u_add.clicked.connect(self.add_url)
        u_del = QPushButton("ลบ url")
        u_del.clicked.connect(self.del_url)
        u_box.addWidget(u_add)
        u_box.addWidget(u_del)
        root.addLayout(u_box)

        self.urls_list = QListWidget()
        self.urls_list.setMinimumHeight(140)
        root.addWidget(self.urls_list)

        self._populate()

    def set_config(self, config: ConfigModel) -> None:
        self.config = config
        self._populate()

    def _skills(self) -> dict:
        s = self.config.data.get("skills")
        if isinstance(s, dict):
            return s
        return {}

    def _populate(self) -> None:
        self.paths_list.clear()
        self.urls_list.clear()
        for p in self._skills().get("paths", []) or []:
            self.paths_list.addItem(str(p))
        for u in self._skills().get("urls", []) or []:
            self.urls_list.addItem(str(u))

    def _ensure(self) -> dict:
        if "skills" not in self.config.data or not isinstance(self.config.data["skills"], dict):
            self.config.data["skills"] = {}
        return self.config.data["skills"]

    def add_path(self) -> None:
        val, ok = QInputDialog.getText(self, "เพิ่ม path", "path ของโฟลเดอร์ skill:")
        if not ok or not val.strip():
            return
        self._ensure()
        self.config.data["skills"].setdefault("paths", []).append(val.strip())
        self._populate()
        self.data_changed.emit()

    def del_path(self) -> None:
        cur = self.paths_list.currentRow()
        if cur < 0:
            return
        self.config.data["skills"].setdefault("paths", []).pop(cur)
        self._populate()
        self.data_changed.emit()

    def add_url(self) -> None:
        val, ok = QInputDialog.getText(self, "เพิ่ม url", "url ของ skill (e.g. https://example.com/.well-known/skills/):")
        if not ok or not val.strip():
            return
        self._ensure()
        self.config.data["skills"].setdefault("urls", []).append(val.strip())
        self._populate()
        self.data_changed.emit()

    def del_url(self) -> None:
        cur = self.urls_list.currentRow()
        if cur < 0:
            return
        self.config.data["skills"].setdefault("urls", []).pop(cur)
        self._populate()
        self.data_changed.emit()

    def commit(self) -> None:
        pass


class PermissionPanel(QWidget):
    """Edits permission[<tool>] as a mode (ask/allow/deny) + optional object form.

    Per schema, each tool rule is either a string mode or an object like
    {"ask": "text", ...}. Known tools are listed; unknown keys are preserved.
    """

    data_changed = Signal()

    def __init__(self, config: ConfigModel, parent=None):
        super().__init__(parent)
        self.config = config
        self._selected_tool = None
        self._building = False

        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        left = QVBoxLayout()
        self.list = QListWidget()
        self.list.currentItemChanged.connect(self._on_select)
        left.addWidget(self.list)

        btns = QHBoxLayout()
        b_add = QPushButton("+ tool")
        b_add.clicked.connect(self.add_tool)
        b_del = QPushButton("ลบ")
        b_del.clicked.connect(self.delete_tool)
        btns.addWidget(b_add)
        btns.addWidget(b_del)
        left.addLayout(btns)

        lw = QWidget()
        lw.setLayout(left)
        lw.setMaximumWidth(240)

        form = QFormLayout()
        self.f_tool_label = QLabel("")
        form.addRow("tool", self.f_tool_label)

        self.f_mode = QComboBox()
        self.f_mode.addItems(PERMISSION_MODES)
        form.addRow("mode", self.f_mode)

        self.f_text = QTextEdit()
        self.f_text.setPlaceholderText('เช่น "ระบุตัวเลือกที่อนุญาต" (รายละเอียดตอน ask)\nวัตถุ {ask|allow|deny: "text"} ตาม schema')
        self.f_text.setMaximumHeight(80)
        form.addRow("ข้อความ/object", self.f_text)

        self.form = QWidget()
        self.form.setLayout(form)

        root.addWidget(lw)
        root.addWidget(self.form, stretch=1)

        self._populate()

    def set_config(self, config: ConfigModel) -> None:
        self.config = config
        self._populate()

    def _perms(self) -> dict:
        p = self.config.data.get("permission")
        if isinstance(p, dict):
            return p
        return {}

    def _populate(self) -> None:
        self._building = True
        self.list.clear()
        self._selected_tool = None
        existing = set(self._perms().keys())
        for t in PERMISSION_TOOLS:
            if t in existing:
                self.list.addItem(QListWidgetItem(f"{t}  ✓"))
            else:
                self.list.addItem(QListWidgetItem(f"{t}  (ไม่ตั้ง)"))
        for t in existing:
            if t not in PERMISSION_TOOLS:
                self.list.addItem(QListWidgetItem(f"{t}  (อื่นๆ)"))
        self.list.setCurrentRow(-1)
        self._building = False
        self._clear_form()

    def _clear_form(self) -> None:
        self.f_tool_label.setText("(ไม่เลือก)")
        self.f_mode.setCurrentText("ask")
        self.f_text.clear()

    def _find_text_for(self, t: str) -> str:
        """Serialize tool item: string or object, for the text area."""
        v = self._perms().get(t)
        if isinstance(v, dict):
            return json.dumps(v, ensure_ascii=False, indent=2)
        if isinstance(v, str):
            return ""
        return ""

    def _find_mode_for(self, t: str) -> str:
        v = self._perms().get(t)
        if isinstance(v, dict):
            for m in PERMISSION_MODES:
                if m in v:
                    return m
            return "ask"
        if isinstance(v, str) and v in PERMISSION_MODES:
            return v
        return "ask"

    def _on_select(self, cur, prev) -> None:
        if self._building or cur is None:
            return
        self._selected_tool = cur.text().split("  (")[0].strip()
        self._selected_tool = self._selected_tool.split("  ✓")[0].strip()
        self.f_tool_label.setText(self._selected_tool)
        v = self._perms().get(self._selected_tool)
        if isinstance(v, str):
            self.f_mode.setCurrentText(v)
            self.f_text.clear()
        elif isinstance(v, dict):
            self.f_mode.setCurrentText(self._find_mode_for(self._selected_tool))
            self.f_text.setPlainText(self._find_text_for(self._selected_tool))
        else:
            self.f_mode.setCurrentText("ask")
            self.f_text.clear()

    def add_tool(self) -> None:
        tool, ok = QInputDialog.getText(self, "เพิ่ม tool", "ชื่อ tool:")
        if not ok or not tool.strip():
            return
        if "permission" not in self.config.data or not isinstance(self.config.data["permission"], dict):
            self.config.data["permission"] = {}
        self.config.data["permission"].setdefault(tool.strip(), "ask")
        self._populate()
        self._select(tool.strip())
        self.data_changed.emit()

    def delete_tool(self) -> None:
        if not self._selected_tool:
            return
        if QMessageBox.question(self, "ลบ", f"ลบ permission ของ '{self._selected_tool}'?") == QMessageBox.Yes:
            self.config.data.get("permission", {}).pop(self._selected_tool, None)
            self._populate()
            self.data_changed.emit()

    def _select(self, tool: str) -> None:
        for i in range(self.list.count()):
            it = self.list.item(i)
            if it.text().split("  ")[0].strip() == tool:
                self.list.setCurrentRow(i)
                return

    def commit(self) -> None:
        if not self._selected_tool:
            return
        if "permission" not in self.config.data or not isinstance(self.config.data["permission"], dict):
            self.config.data["permission"] = {}
        perms = self.config.data["permission"]
        mode = self.f_mode.currentText()
        body = self.f_text.toPlainText().strip()
        if body:
            try:
                obj = json.loads(body)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "permission object ไม่ใช่ JSON", "ไม่บันทึกข้อความ object")
                obj = None
            if obj is not None and isinstance(obj, dict):
                if mode in obj:
                    perms[self._selected_tool] = obj
                else:
                    perms[self._selected_tool] = {mode: body}
            elif obj is not None and isinstance(obj, str):
                perms[self._selected_tool] = obj
            else:
                perms[self._selected_tool] = mode
        else:
            perms[self._selected_tool] = mode
