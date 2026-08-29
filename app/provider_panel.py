"""Provider / Model editing: navigation tree + form editors.

Layout: left QTreeWidget of providers and their models, right a stacked set of
forms -- one for a selected provider, one for a selected model.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QStackedWidget,
    QFormLayout,
    QLineEdit,
    QComboBox,
    QCheckBox,
    QPushButton,
    QGroupBox,
    QScrollArea,
    QLabel,
    QMessageBox,
    QDoubleSpinBox,
    QSpinBox,
    QTextEdit,
)

from .config_model import ConfigModel, parse_money


class ProviderPanel(QWidget):
    data_changed = Signal()

    def __init__(self, config: ConfigModel, parent=None):
        super().__init__(parent)
        self.config = config
        self._selected_provider = None
        self._selected_model = None
        self._building = False

        self._build_ui()
        self._populate()

    # ---- construction ----------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # Left: navigation tree + add buttons
        left = QVBoxLayout()
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_selection)
        left.addWidget(self.tree)

        btns = QHBoxLayout()
        btn_add_provider = QPushButton("+ Provider")
        btn_add_provider.clicked.connect(self.add_provider)
        btn_add_model = QPushButton("+ Model")
        btn_add_model.clicked.connect(self.add_model)
        btn_del = QPushButton("ลบ")
        btn_del.clicked.connect(self.delete_selected)
        btns.addWidget(btn_add_provider)
        btns.addWidget(btn_add_model)
        btns.addWidget(btn_del)
        left.addLayout(btns)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(320)

        # Right: stacked forms
        self.stack = QStackedWidget()

        self.build_provider_form()
        self.build_model_form()

        root.addWidget(left_widget)
        root.addWidget(self.stack, stretch=1)

    def build_provider_form(self) -> None:
        w = QWidget()
        form = QFormLayout(w)

        self.f_npm = QLineEdit()
        self.f_name = QLineEdit()
        self.f_baseurl = QLineEdit()
        self.f_apikey = QLineEdit()
        self.f_apikey.setEchoMode(QLineEdit.Password)
        self.f_whitelist = QTextEdit()
        self.f_whitelist.setPlaceholderText("หนึ่ง model ต่อบรรทัด (whitelist)")

        form.addRow("npm", self.f_npm)
        form.addRow("name", self.f_name)
        form.addRow("baseURL", self.f_baseurl)
        form.addRow("apiKey", self.f_apikey)
        form.addRow("whitelist", self.f_whitelist)

        self.provider_form = w
        self.stack.addWidget(w)

    def build_model_form(self) -> None:
        w = QWidget()
        form = QFormLayout(w)

        self.m_id = QLineEdit()
        self.m_name = QLineEdit()
        self.m_reasoning = QCheckBox("reasoning")
        self.m_tool_call = QCheckBox("tool_call")

        self.m_context = QSpinBox()
        self.m_context.setRange(0, 10_000_000)
        self.m_context.setSuffix(" tokens")
        self.m_output = QSpinBox()
        self.m_output.setRange(0, 10_000_000)
        self.m_output.setSuffix(" tokens")

        self.m_cost_in = QDoubleSpinBox()
        self.m_cost_in.setRange(0, 1_000_000)
        self.m_cost_in.setDecimals(4)
        self.m_cost_out = QDoubleSpinBox()
        self.m_cost_out.setRange(0, 1_000_000)
        self.m_cost_out.setDecimals(4)
        self.m_cost_cache_read = QDoubleSpinBox()
        self.m_cost_cache_read.setRange(0, 1_000_000)
        self.m_cost_cache_read.setDecimals(4)
        self.m_cost_cache_write = QDoubleSpinBox()
        self.m_cost_cache_write.setRange(0, 1_000_000)
        self.m_cost_cache_write.setDecimals(4)

        self.m_options = QTextEdit()
        self.m_options.setPlaceholderText("JSON options เช่น {\"image\": true, ...}")

        form.addRow("id", self.m_id)
        form.addRow("display name", self.m_name)
        form.addRow("", self.m_reasoning)
        form.addRow("", self.m_tool_call)
        form.addRow("limit.context", self.m_context)
        form.addRow("limit.output", self.m_output)
        form.addRow("cost.input", self.m_cost_in)
        form.addRow("cost.output", self.m_cost_out)
        form.addRow("cost.cache_read", self.m_cost_cache_read)
        form.addRow("cost.cache_write", self.m_cost_cache_write)
        form.addRow("options (JSON)", self.m_options)

        note = QLabel("* ราคาต่อ 1M tokens ตาม convention ของ opencode")
        note.setStyleSheet("color:#888;")
        form.addRow(note)

        self.model_form = w
        self.stack.addWidget(w)

    # ---- population ------------------------------------------------------

    def set_config(self, config: ConfigModel) -> None:
        self.config = config
        self._populate()

    def _populate(self) -> None:
        self._building = True
        self.tree.clear()
        self._selected_provider = None
        self._selected_model = None

        for pname, pdata in self.config.providers.items():
            pitem = QTreeWidgetItem([pname])
            pitem.setData(0, Qt.UserRole, ("provider", pname))
            self.tree.addTopLevelItem(pitem)
            models = pdata.get("models") if isinstance(pdata, dict) else None
            if isinstance(models, dict):
                for mkey in models.keys():
                    mitem = QTreeWidgetItem([mkey])
                    mitem.setData(0, Qt.UserRole, ("model", pname, mkey))
                    pitem.addChild(mitem)
            pitem.setExpanded(True)

        self.tree.setCurrentItem(None)
        self.stack.setCurrentIndex(0)
        self._building = False

    # ---- selection -------------------------------------------------------

    def _on_selection(self) -> None:
        if self._building:
            return
        items = self.tree.selectedItems()
        if not items:
            return
        item = items[0]
        kind = item.data(0, Qt.UserRole)
        if kind[0] == "provider":
            self._show_provider(kind[1])
        elif kind[0] == "model":
            self._show_model(kind[1], kind[2])

    def _show_provider(self, pname: str) -> None:
        self._selected_provider = pname
        p = self.config.provider(pname) or {}
        self.f_npm.setText(str(p.get("npm", "")))
        self.f_name.setText(str(p.get("name", "")))
        self.f_baseurl.setText(str(p.get("options", {}).get("baseURL", "")))
        self.f_apikey.setText(str(p.get("options", {}).get("apiKey", "")))
        whitelist = p.get("whitelist", [])
        self.f_whitelist.setPlainText("\n".join(whitelist) if isinstance(whitelist, list) else "")
        self.stack.setCurrentIndex(0)

    def _show_model(self, pname: str, mkey: str) -> None:
        self._selected_provider = pname
        self._selected_model = mkey
        p = self.config.provider(pname) or {}
        m = p.get("models", {}).get(mkey, {}) if isinstance(p, dict) else {}

        self.m_id.setText(str(m.get("id", mkey)))
        self.m_name.setText(str(m.get("name", "")))
        self.m_reasoning.setChecked(bool(m.get("reasoning", False)))
        self.m_tool_call.setChecked(bool(m.get("tool_call", False)))

        limit = m.get("limit", {}) or {}
        self.m_context.setValue(int(limit.get("context", 0) or 0))
        self.m_output.setValue(int(limit.get("output", 0) or 0))

        cost = m.get("cost", {}) or {}
        self.m_cost_in.setValue(parse_money(cost.get("input")) or 0)
        self.m_cost_out.setValue(parse_money(cost.get("output")) or 0)
        self.m_cost_cache_read.setValue(parse_money(cost.get("cache_read")) or 0)
        self.m_cost_cache_write.setValue(parse_money(cost.get("cache_write")) or 0)

        import json

        opts = m.get("options", {}) or {}
        self.m_options.setPlainText(json.dumps(opts, ensure_ascii=False, indent=2) if opts else "")
        self.stack.setCurrentIndex(1)

    # ---- mutation --------------------------------------------------------

    def add_provider(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        name, ok = QInputDialog.getText(self, "เพิ่ม Provider", "ชื่อ provider:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if not self.config.add_provider(name):
            return
        self._populate()
        self._find_and_select_provider(name)
        self._mark_changed()

    def add_model(self) -> None:
        from PySide6.QtWidgets import QInputDialog

        pname = self._selected_provider
        if not pname:
            QMessageBox.information(self, "เพิ่ม Model", "เลือก provider ก่อน")
            return
        mkey, ok = QInputDialog.getText(self, "เพิ่ม Model", f"model key (ใต้ {pname}):")
        if not ok or not mkey.strip():
            return
        mkey = mkey.strip()
        p = self.config.add_provider(pname)
        p.setdefault("models", {})[mkey] = {}
        self._populate()
        self._find_and_select_model(pname, mkey)
        self._mark_changed()

    def delete_selected(self) -> None:
        items = self.tree.selectedItems()
        if not items:
            return
        item = items[0]
        kind = item.data(0, Qt.UserRole)
        if kind[0] == "provider":
            if QMessageBox.question(self, "ลบ", f"ลบ provider '{kind[1]}'?") == QMessageBox.Yes:
                self.config.remove_provider(kind[1])
        else:
            _, pname, mkey = kind
            if QMessageBox.question(self, "ลบ", f"ลบ model '{mkey}'?") == QMessageBox.Yes:
                self.config.provider(pname).get("models", {}).pop(mkey, None)
        self._populate()
        self._mark_changed()

    # ---- commit ----------------------------------------------------------

    def commit(self) -> None:
        """Write pending field values into config.data for whichever is selected."""
        if self._selected_provider:
            # Provider form (always show latest, harmless to re-commit selected provider)
            if self.stack.currentIndex() == 0:
                self._commit_provider_fields()
            if self._selected_model and self.stack.currentIndex() == 1:
                self._commit_model_fields()

    def _commit_provider_fields(self) -> None:
        pname = self._selected_provider
        p = self.config.add_provider(pname)
        if self.f_npm.text():
            p["npm"] = self.f_npm.text()
        else:
            p.pop("npm", None)
        if self.f_name.text():
            p["name"] = self.f_name.text()
        else:
            p.pop("name", None)
        opts = p.setdefault("options", {})
        if self.f_baseurl.text():
            opts["baseURL"] = self.f_baseurl.text()
        else:
            opts.pop("baseURL", None)
        if self.f_apikey.text():
            opts["apiKey"] = self.f_apikey.text()
        else:
            opts.pop("apiKey", None)
        if not opts:
            p.pop("options", None)
        wl = [s.strip() for s in self.f_whitelist.toPlainText().splitlines() if s.strip()]
        if wl:
            p["whitelist"] = wl
        else:
            p.pop("whitelist", None)

    def _commit_model_fields(self) -> None:
        import json

        pname, mkey = self._selected_provider, self._selected_model
        p = self.config.add_provider(pname)
        models = p.setdefault("models", {})
        m = models.setdefault(mkey, {})
        if self.m_id.text():
            m["id"] = self.m_id.text()
        if self.m_name.text():
            m["name"] = self.m_name.text()
        else:
            m.pop("name", None)
        m["reasoning"] = self.m_reasoning.isChecked()
        m["tool_call"] = self.m_tool_call.isChecked()
        limit = {}
        if self.m_context.value():
            limit["context"] = self.m_context.value()
        if self.m_output.value():
            limit["output"] = self.m_output.value()
        if limit:
            m["limit"] = limit
        else:
            m.pop("limit", None)
        cost = {}
        for val, key in [
            (self.m_cost_in.value(), "input"),
            (self.m_cost_out.value(), "output"),
            (self.m_cost_cache_read.value(), "cache_read"),
            (self.m_cost_cache_write.value(), "cache_write"),
        ]:
            if val:
                cost[key] = val
        if cost:
            m["cost"] = cost
        else:
            m.pop("cost", None)
        txt = self.m_options.toPlainText().strip()
        if txt:
            try:
                m["options"] = json.loads(txt)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "options ไม่ใช่ JSON", "ข้ามตัว options (ไม่บันทึก)")
        else:
            m.pop("options", None)

    # ---- helpers ---------------------------------------------------------

    def _mark_changed(self) -> None:
        self.data_changed.emit()

    def _find_and_select_provider(self, pname: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.text(0) == pname:
                self.tree.setCurrentItem(it)
                return

    def _find_and_select_model(self, pname: str, mkey: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            it = self.tree.topLevelItem(i)
            if it.text(0) == pname:
                for j in range(it.childCount()):
                    c = it.child(j)
                    if c.text(0) == mkey:
                        self.tree.setCurrentItem(c)
                        return
