"""Provider / Model editing: navigation tree + form editors.

Layout: left QTreeWidget of providers and their models, right a stacked set of
forms -- one for a selected provider, one for a selected model.

Models can be reordered via drag-and-drop within the same provider.
"""
from __future__ import annotations

from typing import Any

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
    QAbstractItemView,
)

from .config_model import ConfigModel, parse_money


class _ReorderTree(QTreeWidget):
    """Tree widget that syncs model order back to config on drop."""

    order_changed = Signal(str)  # provider name

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDefaultDropAction(Qt.MoveAction)

    def dropEvent(self, event):
        dragged = self.currentItem()
        if not dragged:
            event.ignore()
            return
        kind = dragged.data(0, Qt.UserRole)
        # Only allow dragging model (child) items, not providers
        if not kind or kind[0] != "model":
            event.ignore()
            return
        # Determine target parent (the provider item)
        target = self.itemAt(event.position().toPoint())
        if target is None:
            event.ignore()
            return
        target_kind = target.data(0, Qt.UserRole)
        if target_kind and target_kind[0] == "model":
            target = target.parent()
        elif target_kind and target_kind[0] == "provider":
            pass  # drop onto provider row itself
        else:
            event.ignore()
            return
        # Only allow same-provider moves
        source_parent = dragged.parent()
        if source_parent is None or target is None or source_parent is not target:
            event.ignore()
            return
        super().dropEvent(event)
        pname = target.text(0) if target else ""
        if pname:
            self.order_changed.emit(pname)


class ProviderPanel(QWidget):
    data_changed = Signal()

    def __init__(self, config: ConfigModel, parent=None):
        super().__init__(parent)
        self.config = config
        self._selected_provider = None
        self._selected_model = None
        # Cost values loaded from the model, so commit can distinguish an
        # untouched QDoubleSpinBox (default 0) from a genuine 0 price.
        self._orig_cost: dict[str, float] = {}
        self._building = False
        self._clipboard_model: dict[str, Any] | None = None

        self._build_ui()
        self._populate()

    # ---- construction ----------------------------------------------------

    def _build_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(4, 4, 4, 4)

        # Left: navigation tree + add buttons
        left = QVBoxLayout()
        self.filter = QLineEdit()
        self.filter.setPlaceholderText("กรอง provider / model...")
        self.filter.textChanged.connect(self._apply_filter)
        left.addWidget(self.filter)

        self.tree = _ReorderTree()
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_selection)
        self.tree.order_changed.connect(self._sync_model_order)
        left.addWidget(self.tree)

        # Row 1: add / delete
        btns1 = QHBoxLayout()
        btn_add_provider = QPushButton("+ Provider")
        btn_add_provider.setToolTip("เพิ่ม provider ใหม่ (ถามชื่อ)")
        btn_add_provider.clicked.connect(self.add_provider)
        btn_add_model = QPushButton("+ Model")
        btn_add_model.setToolTip("เพิ่ม model ใหม่ใน provider ที่เลือก (ถาม key)")
        btn_add_model.clicked.connect(self.add_model)
        btn_del = QPushButton("ลบรายการ")
        btn_del.setToolTip("ลบ provider หรือ model ที่เลือกอยู่ (ถามยืนยันก่อน)")
        btn_del.clicked.connect(self.delete_selected)
        for b in (btn_add_provider, btn_add_model, btn_del):
            b.setMinimumHeight(30)
            btns1.addWidget(b)
        left.addLayout(btns1)

        # Row 2: copy / paste model
        btns2 = QHBoxLayout()
        btn_copy = QPushButton("คัดลอก model")
        btn_copy.setToolTip("คัดลอก model ที่เลือก (ค่า limit/cost/options ทั้งหมด)")
        btn_copy.clicked.connect(self.copy_model)
        btn_paste = QPushButton("วาง model")
        btn_paste.setToolTip("วาง model ที่คัดลอกไว้ลง provider ที่เลือก (ถาม key ใหม่)")
        btn_paste.clicked.connect(self.paste_model)
        for b in (btn_copy, btn_paste):
            b.setMinimumHeight(30)
            btns2.addWidget(b)
        left.addLayout(btns2)

        # Row 3: view + batch tools
        btns3 = QHBoxLayout()
        btn_expand = QPushButton("ขยายทั้งหมด")
        btn_expand.setToolTip("ขยาย tree ให้เห็นทุก model")
        btn_expand.clicked.connect(self.tree.expandAll)
        btn_collapse = QPushButton("ย่อทั้งหมด")
        btn_collapse.setToolTip("ย่อ tree เหลือแค่ provider")
        btn_collapse.clicked.connect(self.tree.collapseAll)
        btn_batch = QPushButton("แก้ทีละหลายตัว")
        btn_batch.setToolTip("ตั้งค่า limit/cost พร้อมกันทุก model ใน provider ที่เลือก")
        btn_batch.clicked.connect(self.batch_edit)
        for b in (btn_expand, btn_collapse, btn_batch):
            b.setMinimumHeight(30)
            btns3.addWidget(b)
        left.addLayout(btns3)

        left_widget = QWidget()
        left_widget.setLayout(left)
        left_widget.setMaximumWidth(380)

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

        api_row = QHBoxLayout()
        api_row.addWidget(self.f_apikey, stretch=1)
        self.btn_apikey = QPushButton("แสดง")
        self.btn_apikey.setCheckable(True)
        self.btn_apikey.setToolTip("แสดง/ซ่อน apiKey")
        self.btn_apikey.toggled.connect(self._toggle_apikey_echo)
        api_row.addWidget(self.btn_apikey)
        api_row.setContentsMargins(0, 0, 0, 0)

        self.f_whitelist = QTextEdit()
        self.f_whitelist.setPlaceholderText("หนึ่ง model ต่อบรรทัด (whitelist)")

        form.addRow("npm", self.f_npm)
        form.addRow("name", self.f_name)
        form.addRow("baseURL", self.f_baseurl)
        form.addRow("apiKey", api_row)
        form.addRow("whitelist", self.f_whitelist)

        net_row = QHBoxLayout()
        self.btn_test_api = QPushButton("ทดสอบ API")
        self.btn_test_api.clicked.connect(self.test_api)
        self.btn_fetch_wl = QPushButton("ดึง whitelist (registry)")
        self.btn_fetch_wl.clicked.connect(self.fetch_whitelist_from_registry)
        net_row.addWidget(self.btn_test_api)
        net_row.addWidget(self.btn_fetch_wl)
        net_row.addStretch()
        form.addRow("", net_row)

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

        # Record which cost boxes the user actually touched, so an explicit 0
        # (free model) is kept while an untouched box (also 0) is not written.
        self._cost_edited: set[str] = set()
        self.m_cost_in.valueChanged.connect(lambda _: self._cost_edited.add("input"))
        self.m_cost_out.valueChanged.connect(lambda _: self._cost_edited.add("output"))
        self.m_cost_cache_read.valueChanged.connect(lambda _: self._cost_edited.add("cache_read"))
        self.m_cost_cache_write.valueChanged.connect(lambda _: self._cost_edited.add("cache_write"))

        self.m_options = QTextEdit()
        self.m_options.setPlaceholderText("JSON options เช่น {\"image\": true, ...}")

        self.m_extra = QTextEdit()
        self.m_extra.setPlaceholderText(
            "key อื่นที่ form ไม่รู้จัก (เช่น interleaved) — ใส่ JSON เช่น {\"interleaved\": {\"field\": \"reasoning_content\"}}\n"
            "ว่าง = ลบ key ที่ไม่รู้จัก (ระวัง: ทั้งหมด)"
        )

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
        form.addRow("extra keys (JSON)", self.m_extra)

        auto_row = QHBoxLayout()
        self.btn_autofill = QPushButton("ดึงค่าอัตโนมัติ (models.dev)")
        self.btn_autofill.clicked.connect(self.autofill_model)
        auto_row.addWidget(self.btn_autofill)
        auto_row.addStretch()
        form.addRow("", auto_row)

        note = QLabel("* ราคาต่อ 1M tokens ตาม convention ของ opencode")
        note.setStyleSheet("color:#888;")
        form.addRow(note)

        self.model_form = w
        self.stack.addWidget(w)

    # ---- population ------------------------------------------------------

    def set_config(self, config: ConfigModel) -> None:
        self.config = config
        self._populate()

    def _toggle_apikey_echo(self, show: bool) -> None:
        self.f_apikey.setEchoMode(QLineEdit.Normal if show else QLineEdit.Password)

    def _apply_filter(self, text: str) -> None:
        needle = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            pitem = self.tree.topLevelItem(i)
            pname = pitem.text(0)
            matched = needle in pname.lower() if needle else True
            visible = matched
            for j in range(pitem.childCount()):
                citem = pitem.child(j)
                cmatched = needle in citem.text(0).lower() if needle else True
                citem.setHidden(not cmatched)
                if cmatched:
                    visible = True
            pitem.setHidden(not visible)
        self.tree.expandAll()

    def _populate(self) -> None:
        self._building = True
        self.tree.clear()
        self._selected_provider = None
        self._selected_model = None
        self._orig_cost = {}
        self._cost_edited = set()

        for pname in sorted(self.config.providers.keys()):
            pdata = self.config.providers[pname]
            pitem = QTreeWidgetItem([pname])
            pitem.setData(0, Qt.UserRole, ("provider", pname))
            self.tree.addTopLevelItem(pitem)
            models = pdata.get("models") if isinstance(pdata, dict) else None
            if isinstance(models, dict):
                for mkey in sorted(models.keys()):
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
        # Commit whatever is currently shown so switching items does not drop
        # in-flight edits (e.g. typed provider name, then user clicks a model).
        self._commit_shown()
        if kind[0] == "provider":
            self._show_provider(kind[1])
        elif kind[0] == "model":
            self._show_model(kind[1], kind[2])

    def _show_provider(self, pname: str) -> None:
        self._selected_provider = pname
        self._orig_cost = {}
        self._cost_edited = set()
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
        self._orig_cost = {
            k: v for k, v in cost.items() if isinstance(v, (int, float)) and v is not None
        }
        self.m_cost_in.setValue(parse_money(cost.get("input")) or 0)
        self.m_cost_out.setValue(parse_money(cost.get("output")) or 0)
        self.m_cost_cache_read.setValue(parse_money(cost.get("cache_read")) or 0)
        self.m_cost_cache_write.setValue(parse_money(cost.get("cache_write")) or 0)
        # setValue() above fires valueChanged; drop those synthetic events so
        # only real user edits count as "touched".
        self._cost_edited.clear()

        import json

        opts = m.get("options", {}) or {}
        self.m_options.setPlainText(json.dumps(opts, ensure_ascii=False, indent=2) if opts else "")
        # Extra keys the form does not understand (interleaved, etc.)
        known = {"id", "name", "reasoning", "tool_call", "limit", "cost", "options"}
        extra = {k: v for k, v in m.items() if k not in known}
        self.m_extra.setPlainText(json.dumps(extra, ensure_ascii=False, indent=2) if extra else "")
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
        self._commit_shown()  # don't drop edits of the currently visible form
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

    def _commit_shown(self) -> None:
        """Commit whichever form is currently visible, if anything selected."""
        if self.stack.currentIndex() == 0 and self._selected_provider:
            self._commit_provider_fields()
        elif self.stack.currentIndex() == 1 and self._selected_model:
            self._commit_model_fields()

    def commit(self) -> None:
        """Write pending field values into config.data for whichever is selected."""
        self._commit_shown()

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
        # Merge instead of rebuild: keep keys the UI does not know about
        # (e.g. "interleaved", "attachment", future schema keys).
        if self.m_id.text():
            m["id"] = self.m_id.text()
        else:
            m.pop("id", None)
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
            # Keep 0 only when it matters: the model already had that cost key
            # (free model), or the user explicitly touched the box (set it to 0).
            if val != 0 or key in self._orig_cost or key in self._cost_edited:
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
        extra_txt = self.m_extra.toPlainText().strip()
        if extra_txt:
            try:
                extra_obj = json.loads(extra_txt)
            except json.JSONDecodeError:
                QMessageBox.warning(self, "extra keys ไม่ใช่ JSON", "ข้ามตัว extra keys (ไม่บันทึก)")
                extra_obj = None
            if extra_obj is not None and isinstance(extra_obj, dict):
                known = {"id", "name", "reasoning", "tool_call", "limit", "cost", "options"}
                for k in list(extra_obj):
                    if k in known:
                        QMessageBox.warning(self, "extra keys ข้ามคีย์ที่รู้จัก",
                                            f"'{k}' เป็นคีย์ของ form ปกติ ไม่บังคับใส่ extra")
                        extra_obj.pop(k)
                for k, v in extra_obj.items():
                    m[k] = v
        else:
            pass  # do NOT drop unknown keys on empty -- merge keeps them

    # ---- helpers ---------------------------------------------------------

    def test_api(self) -> None:
        """Probe {baseURL}/models with the current apiKey, show result."""
        pname = self._selected_provider
        if not pname:
            QMessageBox.information(self, "ทดสอบ API", "เลือก provider ก่อน")
            return
        base = self.f_baseurl.text().strip()
        if not base:
            QMessageBox.warning(self, "ทดสอบ API", "ยังไม่มี baseURL (กรอกก่อนทดสอบ)")
            return
        from .model_registry import test_provider_api

        self.btn_test_api.setEnabled(False)
        self.btn_test_api.setText("กำลังทดสอบ...")
        try:
            res = test_provider_api(base, self.f_apikey.text().strip())
        finally:
            self.btn_test_api.setEnabled(True)
            self.btn_test_api.setText("ทดสอบ API")
        if not res.get("ok"):
            QMessageBox.warning(self, "ทดสอบ API", f"{pname}:\n{res.get('message', 'ไม่สำเร็จ')}")
            return
        models = res.get("models")
        msg = res.get("message", "")
        if models and self._selected_provider:
            # suggest whitelist (semi-protective: ask first)
            ans = QMessageBox.question(
                self, "ทดสอบ API",
                f"{msg}\n\nต้องการเติมรายชื่อ model ทั้งหมดที่เจอ ({len(models)} ตัว) ลง whitelist หรือไม่?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if ans == QMessageBox.Yes:
                current = set(s.strip() for s in self.f_whitelist.toPlainText().splitlines() if s.strip())
                for m in models:
                    current.add(m)
                self.f_whitelist.setPlainText("\n".join(sorted(current)))
                self._mark_changed()
                QMessageBox.information(self, "ทดสอบ API", f"เติม whitelist แล้ว ({len(current)} รายการ)")
        else:
            QMessageBox.information(self, "ทดสอบ API", msg)

    def fetch_whitelist_from_registry(self) -> None:
        """Fill whitelist from models.dev registry for this provider name."""
        pname = self._selected_provider
        if not pname:
            QMessageBox.information(self, "ดึง whitelist", "เลือก provider ก่อน")
            return
        from .model_registry import search_models

        self.btn_fetch_wl.setEnabled(False)
        self.btn_fetch_wl.setText("กำลังดึง...")
        try:
            ids = search_models(pname)
        finally:
            self.btn_fetch_wl.setEnabled(True)
            self.btn_fetch_wl.setText("ดึง whitelist (registry)")
        if not ids:
            QMessageBox.information(
                self, "ดึง whitelist",
                f"ไม่พบ provider '{pname}' ใน registry models.dev\n(เฉพาะ provider ใน registry เท่านั้น supporting)",
            )
            return
        current = set(s.strip() for s in self.f_whitelist.toPlainText().splitlines() if s.strip())
        current.update(ids)
        self.f_whitelist.setPlainText("\n".join(sorted(current)))
        self._mark_changed()
        QMessageBox.information(self, "ดึง whitelist", f"เติมแล้ว ({len(current)} รายการจาก registry)")

    def autofill_model(self) -> None:
        """Fill limit/cost/reasoning/tool_call from models.dev for the current model."""
        pname, mkey = self._selected_provider, self._selected_model
        if not pname or not mkey:
            QMessageBox.information(self, "ดึงค่าอัตโนมัติ", "เลือก model ก่อน")
            return
        from .model_registry import find_model_info

        self.btn_autofill.setEnabled(False)
        self.btn_autofill.setText("กำลังค้นหา...")
        try:
            info = find_model_info(pname, mkey)
        finally:
            self.btn_autofill.setEnabled(True)
            self.btn_autofill.setText("ดึงค่าอัตโนมัติ (models.dev)")
        if not info:
            QMessageBox.information(
                self, "ดึงค่าอัตโนมัติ",
                f"ไม่พบ '{pname}/{mkey}' ใน models.dev\nกรอกเอง (หรือใช้ปุ่มทดสอบ API ของ provider)",
            )
            return

        import json as _json

        lim = info.get("limit") or {}
        cost = info.get("cost") or {}
        if lim.get("context") is not None:
            self.m_context.setValue(int(lim["context"]))
        if lim.get("output") is not None:
            self.m_output.setValue(int(lim["output"]))
        if cost.get("input") is not None:
            self.m_cost_in.setValue(float(cost["input"]))
        if cost.get("output") is not None:
            self.m_cost_out.setValue(float(cost["output"]))
        if cost.get("cache_read") is not None:
            self.m_cost_cache_read.setValue(float(cost["cache_read"]))
        if cost.get("cache_write") is not None:
            self.m_cost_cache_write.setValue(float(cost["cache_write"]))
        self.m_reasoning.setChecked(bool(info.get("reasoning", False)))
        self.m_tool_call.setChecked(bool(info.get("tool_call", False)))
        if info.get("name"):
            self.m_name.setText(str(info["name"]))
        # merge options-ish data (interleaved etc.) into extra keys
        extra: dict[str, Any] = {}
        if isinstance(info.get("interleaved"), dict):
            extra["interleaved"] = info["interleaved"]
        if isinstance(info.get("options"), dict):
            for k, v in info["options"].items():
                extra.setdefault(k, v)
        if extra:
            current = self.m_extra.toPlainText().strip()
            merged: dict[str, Any] = {}
            if current:
                try:
                    parsed = _json.loads(current)
                    if isinstance(parsed, dict):
                        merged.update(parsed)
                except _json.JSONDecodeError:
                    pass
            merged.update(extra)
            self.m_extra.setPlainText(_json.dumps(merged, ensure_ascii=False, indent=2))
        self._mark_changed()
        found = []
        if lim: found.append("limit")
        if cost: found.append("cost")
        found.append("ความจุ")
        QMessageBox.information(self, "ดึงค่าอัตโนมัติ", f"เติมแล้วจาก models.dev (ต่อไปนี้: {', '.join(found)})")

    def _sync_model_order(self, pname: str) -> None:
        """Rebuild the provider's models dict to match the new tree order after drag-drop."""
        for i in range(self.tree.topLevelItemCount()):
            pitem = self.tree.topLevelItem(i)
            if pitem.text(0) != pname:
                continue
            old = self.config.provider(pname).get("models", {})
            if not isinstance(old, dict):
                return
            new: dict[str, Any] = {}
            for j in range(pitem.childCount()):
                mitem = pitem.child(j)
                mkey = mitem.text(0)
                if mkey in old:
                    new[mkey] = old[mkey]
                else:
                    new[mkey] = {}
            # preserve any models not shown in tree (should not happen)
            for k, v in old.items():
                if k not in new:
                    new[k] = v
            self.config.provider(pname)["models"] = new
            self._mark_changed()
            return

    def copy_model(self) -> None:
        """Copy the selected model (deep copy) into the internal clipboard."""
        if not self._selected_model or not self._selected_provider:
            QMessageBox.information(self, "คัดลอก", "เลือก model ก่อน")
            return
        import copy as _copy

        m = self.config.provider(self._selected_provider).get("models", {}).get(self._selected_model)
        if not isinstance(m, dict):
            QMessageBox.information(self, "คัดลอก", "model ไม่มีข้อมูล")
            return
        self._clipboard_model = _copy.deepcopy(m)
        self._status(f"คัดลอก model '{self._selected_model}' แล้ว")

    def paste_model(self) -> None:
        """Paste the copied model into the currently selected provider (or new key)."""
        if self._clipboard_model is None:
            QMessageBox.information(self, "วาง", "ยังไม่มี model ในคลิปบอร์ด (กด 'คัดลอก' ก่อน)")
            return
        from PySide6.QtWidgets import QInputDialog

        pname = self._selected_provider
        if not pname:
            QMessageBox.information(self, "วาง", "เลือก provider ปลายทางก่อน")
            return
        mkey, ok = QInputDialog.getText(
            self, "วาง Model", f"model key ใหม่ (ใต้ {pname}):",
            text=self._selected_model or "copy",
        )
        if not ok or not mkey.strip():
            return
        mkey = mkey.strip()
        import copy as _copy

        p = self.config.add_provider(pname)
        p.setdefault("models", {})[mkey] = _copy.deepcopy(self._clipboard_model)
        self._populate()
        self._find_and_select_model(pname, mkey)
        self._mark_changed()
        self._status(f"วาง model '{mkey}' แล้ว")

    def batch_edit(self) -> None:
        """Apply a field value to all models of a provider at once."""
        from PySide6.QtWidgets import (
            QDialog, QDialogButtonBox, QComboBox as _QC, QSpinBox as _QS,
            QDoubleSpinBox as _QDS, QLabel as _QL, QVBoxLayout as _QVL,
        )

        dlg = QDialog(self)
        dlg.setWindowTitle("แก้หลาย model พร้อมกัน")
        lay = _QVL(dlg)

        lay.addWidget(_QL("Provider:"))
        prov_sel = _QC()
        prov_sel.addItems(sorted(self.config.providers.keys()))
        lay.addWidget(prov_sel)

        lay.addWidget(_QL("Field:"))
        field_sel = _QC()
        field_sel.addItems(["limit.context", "limit.output", "cost.input",
                            "cost.output", "cost.cache_read", "cost.cache_write"])
        lay.addWidget(field_sel)

        lay.addWidget(_QL("ค่า (0 = ลบ field นั้น):"))
        val_spin = _QDS()
        val_spin.setRange(0, 10_000_000)
        val_spin.setDecimals(4)
        lay.addWidget(val_spin)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay.addWidget(buttons)

        if dlg.exec() != QDialog.Accepted:
            return
        pname = prov_sel.currentText()
        field = field_sel.currentText()
        value = val_spin.value()
        section, key = field.split(".")

        changed = 0
        models = self.config.provider(pname).get("models", {})
        for m in models.values():
            if not isinstance(m, dict):
                continue
            if value == 0:
                target = m.get(section)
                if isinstance(target, dict):
                    target.pop(key, None)
                changed += 1
            else:
                target = m.setdefault(section, {})
                if isinstance(target, dict):
                    target[key] = value
                    changed += 1
        self._populate()
        self._mark_changed()
        QMessageBox.information(self, "แก้หลายตัว", f"อัปเดต {changed} model ใน '{pname}'")

    def _status(self, msg: str) -> None:
        parent = self.parent()
        if parent is not None and hasattr(parent, "_status"):
            parent._status(msg)

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
