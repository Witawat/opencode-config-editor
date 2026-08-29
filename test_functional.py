"""End-to-end functional test: drive the real widgets, save, reload, verify.

Run with:  .venv\\Scripts\\python.exe test_functional.py [path-to-config-copy]
Uses a COPY -- never the user's real config.
"""
from __future__ import annotations

import json
import os
import sys
import tempfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.config_model import ConfigModel
from app.main_window import MainWindow


def ok(cond: bool, msg: str) -> None:
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    if not cond:
        raise AssertionError(msg)


def main() -> int:
    src = sys.argv[1] if len(sys.argv) > 1 else ConfigModel.DEFAULT_CONFIG_PATH
    with open(src, "r", encoding="utf-8") as fh:
        original = json.load(fh)

    tmp = os.path.join(tempfile.gettempdir(), "opencode_e2e_test.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(original, fh, ensure_ascii=False)

    app = QApplication.instance() or QApplication([])
    config = ConfigModel.load(tmp)
    win = MainWindow(config)
    win.show()

    print("== Provider tab ==")
    win.stack.setCurrentIndex(0)
    # select first provider (commandcode)
    pname = list(config.providers.keys())[0]
    win.nav._find_and_select_provider(pname)
    win.nav.f_name.setText("E2E Renamed Provider")
    win.nav.f_baseurl.setText("https://e2e.example/v1")
    # auto-fill model values via (mocked) registry -- real registry lookup
    win.nav._find_and_select_model(pname, list(config.providers[pname].get("models", {}).keys())[0])
    win.nav.stack.setCurrentIndex(1)
    # add a brand new model through the real dialog path
    from PySide6.QtWidgets import QInputDialog
    from unittest import mock
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("e2e/model-x", True))):
        win.nav.add_model()
    win.nav.m_name.setText("E2E Model X")
    win.nav.m_options.setPlainText('{"image": true, "service_tier": "priority"}')
    # simulate the user setting input cost to 0 (free model): 0.5 then back to 0
    win.nav.m_cost_in.setValue(0.5)
    win.nav.m_cost_in.setValue(0)
    win.nav.stack.setCurrentIndex(1)

    print("== MCP tab ==")
    win.stack.setCurrentIndex(1)
    mcp_item = win.mcp_tab.list.item(0)
    if mcp_item is not None:
        win.mcp_tab.list.setCurrentItem(mcp_item)
        win.mcp_tab.f_enabled.setChecked(True)

    print("== Agent tab ==")
    win.stack.setCurrentIndex(2)
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("e2e-agent", True))):
        win.agent_tab.add_agent()
    win.agent_tab.f_model.setText("e2e/agent-model")
    win.agent_tab.f_prompt.setPlainText("E2E prompt shorthand")
    win.agent_tab.commit()

    print("== Skill tab ==")
    win.stack.setCurrentIndex(3)
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("D:\\e2e\\skills", True))):
        win.skill_tab.add_path()
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("https://e2e.example/.well-known/skills/", True))):
        win.skill_tab.add_url()

    print("== Permission tab ==")
    win.stack.setCurrentIndex(4)
    win.perm_tab._select("bash")
    win.perm_tab.f_mode.setCurrentText("deny")
    win.perm_tab.commit()

    print("== Global tab (model/instructions/whitelist/blacklist/compaction) ==")
    win.stack.setCurrentIndex(5)
    win.global_tab.f_model.setText("e2e/global-model")
    win.global_tab.f_small_model.setText("e2e/global-small")
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("D:\\e2e\\instruction.md", True))):
        win.global_tab.add_instruction()
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("e2e-whitelisted-provider", True))):
        win.global_tab.add_enabled()
    with mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("e2e-blacklisted-provider", True))):
        win.global_tab.add_disabled()
    win.global_tab.commit()

    print("== JSON Preview tab ==")
    win.stack.setCurrentIndex(6)
    preview_text = win.preview.text.toPlainText()
    ok("apiKey" in preview_text and "***" in preview_text, "preview masks secrets")
    ok("user_3R72" not in preview_text, "no real apiKey leaked into preview")

    print("== Save ==")
    win.save()
    ok(not win._dirty, "dirty flag cleared after save")

    print("== Reload + verify ==")
    reloaded = ConfigModel.load(tmp)
    r = reloaded.data
    ok(r["provider"][pname]["name"] == "E2E Renamed Provider", "provider name saved")
    ok(r["provider"][pname]["options"]["baseURL"] == "https://e2e.example/v1", "baseURL saved")
    ok("e2e/model-x" in r["provider"][pname]["models"], "new model exists")
    m = r["provider"][pname]["models"]["e2e/model-x"]
    ok(m["name"] == "E2E Model X", "model name saved")
    ok(m["options"] == {"image": True, "service_tier": "priority"}, "model options saved")
    ok(m["cost"] == {"input": 0.0} or m["cost"] == {"input": 0}, "cost 0 kept")
    ok(r["agent"]["e2e-agent"]["model"] == "e2e/agent-model", "agent saved")
    ok(r["agent"]["e2e-agent"]["prompt"] == "E2E prompt shorthand", "agent prompt saved")
    ok("D:\\e2e\\skills" in r["skills"]["paths"], "skill path saved")
    ok("https://e2e.example/.well-known/skills/" in r["skills"]["urls"], "skill url saved")
    ok(r["permission"]["bash"] == "deny", "permission saved")
    ok(r["model"] == "e2e/global-model", "global model saved")
    ok(r["small_model"] == "e2e/global-small", "global small_model saved")
    ok("D:\\e2e\\instruction.md" in r["instructions"], "instruction saved")
    ok("e2e-whitelisted-provider" in r["enabled_providers"], "whitelist saved")
    ok("e2e-blacklisted-provider" in r["disabled_providers"], "blacklist saved")

    print("== Preserve original unknown keys ==")
    for pname2, pdat in original.get("provider", {}).items():
        for mk, mv in (pdat.get("models") or {}).items():
            if isinstance(mv, dict) and "interleaved" in mv:
                ok("interleaved" in r["provider"][pname2]["models"][mk],
                   f"interleaved kept for {pname2}/{mk}")
                break

    win.close()
    os.remove(tmp)
    print("ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
