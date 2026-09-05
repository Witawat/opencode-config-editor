"""Unit tests for round-trip correctness of the config editor.

Run with:  .venv\\Scripts\\python.exe test_roundtrip.py
"""
from __future__ import annotations

import copy
import json
import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from app.config_model import ConfigModel, parse_money
from app.provider_panel import ProviderPanel
from app.mcp_panel import MCPPanel
from app.misc_panels import AgentPanel, SkillPanel, PermissionPanel
from app.global_panel import GlobalPanel
from app.preview_panel import mask_secrets
from app import model_registry


def _app() -> QApplication:
    return QApplication.instance() or QApplication([])


def _patch_message_boxes() -> None:
    """QMessageBox/QInputDialog block forever under offscreen; silence dialogs."""
    from unittest import mock

    from PySide6.QtWidgets import QMessageBox, QInputDialog

    patcher = mock.patch.object(QMessageBox, "warning", staticmethod(lambda *a, **k: None))
    patcher.start()
    patcher = mock.patch.object(QMessageBox, "question", staticmethod(lambda *a, **k: QMessageBox.Yes))
    patcher.start()
    patcher = mock.patch.object(QMessageBox, "information", staticmethod(lambda *a, **k: None))
    patcher.start()
    patcher = mock.patch.object(QInputDialog, "getText", staticmethod(lambda *a, **k: ("", False)))
    patcher.start()


class TestParseMoney(unittest.TestCase):
    def test_empty_is_none(self):
        self.assertIsNone(parse_money(""))
        self.assertIsNone(parse_money(None))

    def test_number_string(self):
        self.assertEqual(parse_money("1.5"), 1.5)
        self.assertEqual(parse_money("0"), 0.0)

    def test_garbage_is_none(self):
        self.assertIsNone(parse_money("abc"))
        self.assertIsNone(parse_money([1, 2]))


class TestProviderRoundTrip(unittest.TestCase):
    """ProviderPanel must not destroy keys it does not know about."""

    def setUp(self):
        _app()
        self.cfg = ConfigModel(data={
            "provider": {
                "demo": {
                    "npm": "@ai-sdk/openai-compatible",
                    "options": {"baseURL": "https://x/v1", "customTls": {"ca": "pem"}},
                    "models": {
                        "m1": {
                            "id": "m1",
                            "interleaved": {"field": "reasoning_content"},
                            "reasoning": True,
                            "tool_call": True,
                            "limit": {"context": 1000000, "output": 65536},
                            "cost": {"input": 0, "output": 0, "cache_read": 0},
                            "unknown_future_key": {"keep": "me"},
                        },
                        "m2": {"name": "second"},
                        "m3": {"name": "third"},
                    },
                }
            }
        })
        self.panel = ProviderPanel(self.cfg)

    def test_interleaved_preserved_on_commit(self):
        self.panel._find_and_select_model("demo", "m1")
        self.panel.stack.setCurrentIndex(1)
        m = self.cfg.provider("demo")["models"]["m1"]
        before = copy.deepcopy(m)
        self.panel._commit_model_fields()
        after = self.cfg.provider("demo")["models"]["m1"]
        self.assertEqual(after.get("interleaved"), before.get("interleaved"))
        self.assertEqual(after.get("unknown_future_key"), {"keep": "me"})

    def test_cost_zero_kept(self):
        self.panel._find_and_select_model("demo", "m1")
        self.panel.stack.setCurrentIndex(1)
        self.panel._commit_model_fields()
        cost = self.cfg.provider("demo")["models"]["m1"]["cost"]
        self.assertEqual(cost, {"input": 0, "output": 0, "cache_read": 0})

    def test_cost_zero_not_invented(self):
        cfg = ConfigModel(data={"provider": {"p": {"models": {"m": {}}}}})
        panel = ProviderPanel(cfg)
        panel._find_and_select_model("p", "m")
        panel.stack.setCurrentIndex(1)
        panel._commit_model_fields()
        self.assertNotIn("cost", cfg.provider("p")["models"]["m"])

    def test_empty_id_popped(self):
        self.panel._find_and_select_model("demo", "m1")
        self.panel.stack.setCurrentIndex(1)
        self.panel.m_id.clear()
        self.panel._commit_model_fields()
        self.assertNotIn("id", self.cfg.provider("demo")["models"]["m1"])

    def test_extra_interleaved_merge(self):
        self.panel._find_and_select_model("demo", "m1")
        self.panel.stack.setCurrentIndex(1)
        self.panel._commit_model_fields()
        m = self.cfg.provider("demo")["models"]["m1"]
        self.assertEqual(m.get("interleaved"), {"field": "reasoning_content"})

    def test_extra_new_key_added(self):
        self.panel._find_and_select_model("demo", "m1")
        self.panel.stack.setCurrentIndex(1)
        self.panel.m_extra.setPlainText('{"future_key2": {"a": 2}}')
        self.panel._commit_model_fields()
        m = self.cfg.provider("demo")["models"]["m1"]
        self.assertEqual(m["future_key2"], {"a": 2})
        self.assertEqual(m["interleaved"], {"field": "reasoning_content"})

    def test_model_reorder_sync(self):
        """_sync_model_order rebuilds models dict in tree order."""
        # Initial order: m1, m2, m3
        tree = self.panel.tree
        pitem = tree.topLevelItem(0)
        self.assertEqual(pitem.childCount(), 3)
        # Simulate swapping m2 and m3 in the tree
        c2 = pitem.takeChild(1)  # remove m2
        pitem.insertChild(2, c2)  # insert at position 2 (after m3)
        self.assertEqual(pitem.child(0).text(0), "m1")
        self.assertEqual(pitem.child(1).text(0), "m3")
        self.assertEqual(pitem.child(2).text(0), "m2")
        # Sync
        self.panel._sync_model_order("demo")
        keys = list(self.cfg.provider("demo")["models"].keys())
        self.assertEqual(keys, ["m1", "m3", "m2"])
        # Values preserved
        self.assertEqual(self.cfg.provider("demo")["models"]["m1"]["id"], "m1")
        self.assertEqual(self.cfg.provider("demo")["models"]["m3"]["name"], "third")

    def test_options_unknown_keys_kept_on_provider(self):
        self.panel._find_and_select_provider("demo")
        self.panel.stack.setCurrentIndex(0)
        self.panel._commit_provider_fields()
        opts = self.cfg.provider("demo")["options"]
        self.assertIn("customTls", opts)
        self.assertEqual(opts["customTls"], {"ca": "pem"})


class TestMCPRoundTrip(unittest.TestCase):
    def setUp(self):
        _app()
        _patch_message_boxes()
        self.cfg = ConfigModel(data={
            "mcp": {
                "srv": {
                    "type": "local",
                    "command": ["npx", "-y", "@playwright/mcp@latest"],
                    "env": {"K": "V"},
                    "enabled": True,
                    "toolbar": ["x"],
                }
            }
        })
        self.panel = MCPPanel(self.cfg)

    def test_command_with_spaces_survives(self):
        srv = self.cfg.mcp["srv"]
        srv["command"] = ["cmd", "--dir", "C:\\Program Files\\app"]
        self.panel.set_config(self.cfg)
        self.panel._select("srv")
        text = self.panel.f_command.text()
        self.assertIn("'C:", text)
        self.panel.commit()
        self.assertEqual(self.cfg.mcp["srv"]["command"],
                         ["cmd", "--dir", "C:\\Program Files\\app"])

    def test_unbalanced_quotes_not_saved(self):
        self.panel._select("srv")
        self.panel.f_command.setText('cmd "unbalanced')
        self.panel.commit()
        # parse failure -> warning + keep previous command untouched
        self.assertEqual(self.cfg.mcp["srv"]["command"],
                         ["npx", "-y", "@playwright/mcp@latest"])

    def test_env_key_env_preserved(self):
        self.panel._select("srv")
        self.panel.f_env.setPlainText('{"K2": "V2"}')
        self.panel.commit()
        srv = self.cfg.mcp["srv"]
        self.assertEqual(srv.get("env"), {"K2": "V2"})
        self.assertNotIn("environment", srv)

    def test_toolbar_key_preserved(self):
        self.panel._select("srv")
        self.panel.commit()
        self.assertEqual(self.cfg.mcp["srv"]["toolbar"], ["x"])


class TestSchemaErrors(unittest.TestCase):
    def test_format(self):
        cfg = ConfigModel(data={"model": 123})
        schema = {
            "type": "object",
            "properties": {"model": {"type": "string"}},
            "additionalProperties": True,
        }
        errors = cfg.schema_errors(schema)
        self.assertEqual(len(errors), 1)
        self.assertRegex(errors[0], r"^model: ")

    def test_long_message_shortened(self):
        long_enum = "x" * 5000
        schema = {"enum": [long_enum]}
        err = ConfigModel(data="not_in_enum").schema_errors(schema)
        self.assertEqual(len(err), 1)
        self.assertTrue(err[0].endswith("…"))
        self.assertLess(len(err[0]), 320)

    def test_shorten_const(self):
        self.assertEqual(ConfigModel._shorten("abc"), "abc")
        self.assertEqual(ConfigModel._shorten("a" * 500, 20), "a" * 20 + " …")

    def test_benign_classification(self):
        from app.main_window import BENIGN_TYPES

        examples = [
            "model: 'inferx/x' is not one of ['302ai/A'",
            "small_model: 'inferx/x' is not one of ['302ai/A'",
            "agent/compaction/model: 'inferx/x' is not one of ['302ai/A'",
            "mcp/srv: {...} is not valid under any of the given schemas",
        ]
        for e in examples:
            self.assertTrue(
                any(k in e and m in e for k, m in BENIGN_TYPES),
                f"should be benign: {e[:40]}",
            )
        real = "provider/x/models/m/limit: {'context': 'oops'} is not of type 'integer'"
        self.assertFalse(any(k in real and m in real for k, m in BENIGN_TYPES))


class TestMiscPanels(unittest.TestCase):
    """Agent/Skill/Permission panels must round-trip and preserve unknown keys."""

    def setUp(self):
        _app()
        _patch_message_boxes()
        self.cfg = ConfigModel(data={
            "agent": {
                "build": {"model": "a/b", "mode": "primary", "prompt": "hi", "unknown": {"z": 1}},
            },
            "skills": {
                "paths": ["D:\\skills"],
                "urls": ["https://example.com/.well-known/skills/"],
                "unknown_key": "keep",
            },
            "permission": {"bash": "allow", "webfetch": {"ask": "ยืนยัน"}, "unknown_tool": {"deny": "x"}},
        })

    def test_agent_preserves_unknown(self):
        panel = AgentPanel(self.cfg)
        panel._select("build")
        panel.f_prompt.setPlainText("new prompt")
        panel.commit()
        a = self.cfg.data["agent"]["build"]
        self.assertEqual(a["unknown"], {"z": 1})
        self.assertEqual(a["prompt"], "new prompt")

    def test_agent_add_and_delete(self):
        panel = AgentPanel(self.cfg)
        # QInputDialog patched to cancel -- verify no crash and no empty name added
        panel.add_agent()
        self.assertNotIn("", self.cfg.data["agent"])

    def test_skill_preserves_unknown(self):
        panel = SkillPanel(self.cfg)
        self.assertEqual(self.cfg.data["skills"]["unknown_key"], "keep")
        panel.commit()
        self.assertEqual(self.cfg.data["skills"]["unknown_key"], "keep")

    def test_permission_modes(self):
        panel = PermissionPanel(self.cfg)
        panel._select("bash")
        self.assertEqual(panel.f_mode.currentText(), "allow")
        panel.f_mode.setCurrentText("deny")
        panel.commit()
        self.assertEqual(self.cfg.data["permission"]["bash"], "deny")

    def test_permission_object_kept(self):
        panel = PermissionPanel(self.cfg)
        panel._select("webfetch")
        panel.commit()
        self.assertEqual(self.cfg.data["permission"]["webfetch"], {"ask": "ยืนยัน"})

    def test_permission_unknown_tool_preserved(self):
        panel = PermissionPanel(self.cfg)
        panel.commit()
        self.assertEqual(self.cfg.data["permission"]["unknown_tool"], {"deny": "x"})


class TestGlobalPanel(unittest.TestCase):
    """model/small_model/instructions/compaction/whitelist/blacklist round-trip."""

    def setUp(self):
        _app()
        _patch_message_boxes()
        self.cfg = ConfigModel(data={
            "model": "a/b",
            "small_model": "c/d",
            "instructions": ["x.md"],
            "compaction": {"auto": True, "tail_turns": 8, "reserved": 250000,
                           "future_key": "keep"},
            "enabled_providers": ["p1"],
            "disabled_providers": ["p2"],
        })
        self.panel = GlobalPanel(self.cfg)

    def test_load_values(self):
        self.assertEqual(self.panel.f_model.text(), "a/b")
        self.assertEqual(self.panel.f_small_model.text(), "c/d")
        self.assertEqual(self.panel.instructions_list.count(), 1)
        self.assertTrue(self.panel.c_auto.isChecked())
        self.assertEqual(self.panel.c_tail_turns.value(), 8)
        self.assertEqual(self.panel.c_reserved.value(), 250000)
        self.assertEqual(self.panel.enabled_list.count(), 1)
        self.assertEqual(self.panel.disabled_list.count(), 1)

    def test_edit_and_commit(self):
        self.panel.f_model.setText("x/y")
        self.panel.f_small_model.setText("z/w")
        self.panel.c_auto.setChecked(False)
        self.panel.c_tail_turns.setValue(16)
        self.panel.commit()
        d = self.cfg.data
        self.assertEqual(d["model"], "x/y")
        self.assertEqual(d["small_model"], "z/w")
        self.assertNotIn("auto", d["compaction"])
        self.assertNotIn("prune", d["compaction"])  # untouched boolean stays absent
        self.assertEqual(d["compaction"]["tail_turns"], 16)
        self.assertIn("future_key", d["compaction"])  # unknown preserved
        self.assertEqual(d["compaction"]["future_key"], "keep")

    def test_enabled_disabled_commit(self):
        self.panel.add_enabled()  # patched dialog -> cancelled, no change
        self.assertEqual(len(self.cfg.data["enabled_providers"]), 1)
        # direct edit through widget list
        self.cfg.data["enabled_providers"].append("p3")
        self.panel.set_config(self.cfg)
        self.panel.commit()
        self.assertEqual(self.cfg.data["enabled_providers"], ["p1", "p3"])

    def test_instructions_commit(self):
        self.cfg.data["instructions"].append("y.md")
        self.panel.set_config(self.cfg)
        self.panel.commit()
        self.assertEqual(self.cfg.data["instructions"], ["x.md", "y.md"])

    def test_cleared_model_popped(self):
        self.panel.f_model.clear()
        self.panel.commit()
        self.assertNotIn("model", self.cfg.data)


class TestModelRegistry(unittest.TestCase):
    """Pure logic parts of the registry auto-fill (no network)."""

    def setUp(self):
        model_registry.reset_cache()
        model_registry._cache = {
            "deepinfra": {
                "id": "deepinfra",
                "models": {
                    "deepseek-ai/DeepSeek-V4-Flash-0731": {
                        "name": "DS V4 Flash",
                        "reasoning": True,
                        "tool_call": True,
                        "limit": {"context": 1024000, "output": 16384},
                        "cost": {"input": 0.08, "output": 0.18},
                    },
                    "Qwen/Qwen3.6-35B-A3B": {"name": "Qwen"},
                },
            },
            "other": {
                "id": "other",
                "models": {"odd/key-extra": {"name": "Odd"}},
            },
        }

    def tearDown(self):
        model_registry.reset_cache()

    def test_find_exact_provider(self):
        info = model_registry.find_model_info("deepinfra", "deepseek-ai/DeepSeek-V4-Flash-0731")
        self.assertIsNotNone(info)
        self.assertEqual(info["limit"]["context"], 1024000)
        self.assertTrue(info["reasoning"])

    def test_find_by_suffix(self):
        info = model_registry.find_model_info("other", "key-extra")
        self.assertIsNotNone(info)
        self.assertEqual(info["name"], "Odd")

    def test_not_found(self):
        self.assertIsNone(model_registry.find_model_info("deepinfra", "nope/xyz"))

    def test_search_models(self):
        ids = model_registry.search_models("deepinfra", "deepseek")
        self.assertIn("deepseek-ai/DeepSeek-V4-Flash-0731", ids)

    def test_search_unknown_provider(self):
        self.assertEqual(model_registry.search_models("fakeprovider"), [])

    def test_test_provider_api_network_error(self):
        with _patch_request_exception():
            res = model_registry.test_provider_api("http://127.0.0.1:1/", timeout=1)
        self.assertFalse(res["ok"])

    def test_derive_options_image(self):
        info = {"attachment": True, "reasoning": True}
        opts = model_registry.derive_options(info)
        self.assertEqual(opts.get("image"), True)

    def test_derive_options_modalities(self):
        info = {"modalities": {"input": ["text", "image"], "output": ["text"]}}
        opts = model_registry.derive_options(info)
        self.assertEqual(opts.get("image"), True)

    def test_derive_options_reasoning_effort(self):
        info = {"reasoning_options": [{"type": "effort", "values": ["low", "high"]}]}
        opts = model_registry.derive_options(info)
        self.assertEqual(opts.get("reasoning_effort"), "low")

    def test_derive_options_interleaved(self):
        info = {"interleaved": {"field": "reasoning_content"}}
        opts = model_registry.derive_options(info)
        self.assertEqual(opts.get("interleaved"), {"field": "reasoning_content"})

    def test_test_model_api_listed_and_ok(self):
        """model listed + completion 200 -> ok."""
        from unittest import mock
        import requests as rq

        class _Resp:
            def __init__(self, code, data=None, text=""):
                self.status_code = code
                self._data = data
                self.text = text

            def close(self):
                pass

            def json(self):
                return self._data

        calls = {"n": 0}

        def fake_get(url, **kw):
            calls["n"] += 1
            return _Resp(200, {"data": [{"id": "test/model"}, {"id": "other"}]})

        def fake_post(url, **kw):
            return _Resp(200, {"id": "x"})

        with mock.patch("app.model_registry.requests.get", side_effect=fake_get), \
             mock.patch("app.model_registry.requests.post", side_effect=fake_post):
            res = model_registry.test_model_api("http://x", "k", "test/model", timeout=1)
        self.assertTrue(res["ok"])
        self.assertIn("ใช้ได้", res["message"])

    def test_test_model_api_not_listed_404(self):
        from unittest import mock

        class _Resp:
            def __init__(self, code, data=None, text=""):
                self.status_code = code
                self._data = data
                self.text = text

            def close(self):
                pass

            def json(self):
                return self._data

        def fake_get(url, **kw):
            return _Resp(200, {"data": [{"id": "other"}]})

        def fake_post(url, **kw):
            return _Resp(404, {"error": {"message": "unknown model"}})

        with mock.patch("app.model_registry.requests.get", side_effect=fake_get), \
             mock.patch("app.model_registry.requests.post", side_effect=fake_post):
            res = model_registry.test_model_api("http://x", "k", "nope/m", timeout=1)
        self.assertFalse(res["ok"])
        self.assertIn("404", res["message"])

    def test_find_max_tokens_binary_search(self):
        from app import model_probe
        from unittest import mock

        class _Resp:
            def __init__(self, code, data=None, text=""):
                self.status_code = code
                self._data = data
                self.text = text

            def close(self):
                pass

            def json(self):
                return self._data

        boundary = 100000  # 200 below, 400 at/above

        def fake_post(url, **kw):
            mt = kw.get("json", {}).get("max_tokens", 0)
            code = 200 if mt < boundary else 400
            return _Resp(code, {})

        with mock.patch("app.model_probe.requests.post", side_effect=fake_post):
            res = model_probe.find_max_tokens("http://x", "k", "m", context=200000, timeout=1)
        self.assertTrue(res["ok"])
        # binary search converges near (but strictly below) boundary
        self.assertLess(res["max_tokens"], boundary)
        self.assertGreaterEqual(res["max_tokens"], boundary - 300)

    def test_detect_reasoning_field(self):
        from app import model_probe
        from unittest import mock

        stream = (
            'data: {"choices":[{"delta":{"reasoning":"thinking..."}}]}\n'
            'data: {"choices":[{"delta":{"content":"hi"}}]}\n'
            'data: [DONE]\n'
        ).encode()

        class _StreamResp:
            status_code = 200

            def iter_lines(self, decode_unicode=True):
                return (line.decode() if isinstance(line, bytes) else line
                        for line in stream.splitlines())

        with mock.patch("app.model_probe.requests.post", return_value=_StreamResp()):
            res = model_probe.detect_reasoning_field("http://x", "k", "m", timeout=1)
        self.assertTrue(res["ok"])
        self.assertEqual(res["field"], "reasoning")

    def test_reasoning_effort_only_low_medium(self):
        from app import model_probe
        from unittest import mock

        class _Resp:
            def __init__(self, code, data=None, text=""):
                self.status_code = code
                self._data = data
                self.text = text

            def close(self):
                pass

            def json(self):
                return self._data

        def fake_post(url, **kw):
            eff = kw.get("json", {}).get("reasoning_effort")
            code = 200 if eff in ("low", "medium") else 400
            return _Resp(code, {})

        with mock.patch("app.model_probe.requests.post", side_effect=fake_post):
            res = model_probe.test_reasoning_effort("http://x", "k", "m", timeout=1)
        self.assertTrue(res["ok"])
        self.assertEqual(res["values"], ["low", "medium"])

    def test_reasoning_effort_custom_values(self):
        """effort_values given (from registry) -> only those are tested."""
        from app import model_probe
        from unittest import mock

        class _Resp:
            def __init__(self, code, data=None, text=""):
                self.status_code = code
                self._data = data
                self.text = text

            def close(self):
                pass

            def json(self):
                return self._data

        tested: list[str] = []

        def fake_post(url, **kw):
            eff = kw.get("json", {}).get("reasoning_effort")
            tested.append(eff)
            code = 200 if eff in ("low", "high") else 400
            return _Resp(code, {})

        with mock.patch("app.model_probe.requests.post", side_effect=fake_post):
            res = model_probe.test_reasoning_effort("http://x", "k", "m", timeout=1,
                                                    effort_values=("low", "high", "max"))
        self.assertEqual(tested, ["low", "high", "max"])  # only given values
        self.assertEqual(res["values"], ["low", "high"])

    def test_reasoning_effort_options_from_registry(self):
        """registry reasoning_options.effort.values -> effort candidates."""
        model_registry.reset_cache()
        model_registry._cache = {
            "myprov": {
                "models": {
                    "m1": {
                        "reasoning_options": [
                            {"type": "effort", "values": ["low", "high", "max"]},
                        ]
                    }
                }
            }
        }
        vals = model_registry.reasoning_effort_options("myprov", "m1")
        self.assertEqual(vals, ["low", "high", "max"])
        # unknown model -> empty (caller falls back to broad set)
        self.assertEqual(model_registry.reasoning_effort_options("myprov", "nope"), [])
        model_registry.reset_cache()

    def test_tool_call_supported(self):
        from app import model_probe
        from unittest import mock

        stream = (
            'data: {"choices":[{"delta":{"content":""}}]}\n'
            'data: {"choices":[{"delta":{},"finish_reason":"tool_calls"}]}\n'
            'data: [DONE]\n'
        ).encode()

        class _StreamResp:
            status_code = 200

            def iter_lines(self, decode_unicode=True):
                return (line.decode() if isinstance(line, bytes) else line
                        for line in stream.splitlines())

        with mock.patch("app.model_probe.requests.post", return_value=_StreamResp()):
            res = model_probe.test_tool_call("http://x", "k", "m", timeout=1)
        self.assertTrue(res["ok"])
        self.assertTrue(res["tool_call"])

    def test_image_support_yes(self):
        from app import model_probe
        from unittest import mock

        class _Resp:
            status_code = 200
            text = ""

            def json(self):
                return {"id": "x"}

        with mock.patch("app.model_probe.requests.post", return_value=_Resp()):
            res = model_probe.test_image_support("http://x", "k", "m", timeout=1)
        self.assertTrue(res["ok"])
        self.assertTrue(res["image"])

    def test_image_support_no(self):
        from app import model_probe
        from unittest import mock

        class _Resp:
            status_code = 400
            text = ""

            def json(self):
                return {}

        with mock.patch("app.model_probe.requests.post", return_value=_Resp()):
            res = model_probe.test_image_support("http://x", "k", "m", timeout=1)
        self.assertTrue(res["ok"])
        self.assertFalse(res["image"])

    def test_image_support_other_error(self):
        from app import model_probe
        from unittest import mock

        class _Resp:
            status_code = 401
            text = ""

            def json(self):
                return {}

        with mock.patch("app.model_probe.requests.post", return_value=_Resp()):
            res = model_probe.test_image_support("http://x", "k", "m", timeout=1)
        self.assertFalse(res["ok"])


def _patch_request_exception():
    """Force requests.get to raise so no real network is touched."""
    from unittest import mock

    import requests as rq

    def _boom(url, **kw):
        raise rq.ConnectionError("test network off")

    return mock.patch("app.model_registry.requests.get", side_effect=_boom)


class TestNewFeatures(unittest.TestCase):
    """Sort / copy-paste / undo-redo / offline schema cache."""

    def setUp(self):
        _app()
        _patch_message_boxes()
        self.cfg = ConfigModel(data={
            "provider": {
                "zeta": {"models": {"b-model": {}, "a-model": {"name": "A"}}},
                "alpha": {"models": {"m1": {"name": "M1"}}},
            }
        })
        self.panel = ProviderPanel(self.cfg)

    def test_populate_sorted(self):
        top = [self.panel.tree.topLevelItem(i).text(0) for i in range(self.panel.tree.topLevelItemCount())]
        self.assertEqual(top, ["alpha", "zeta"])  # sorted alphabetically
        zeta = self.panel.tree.topLevelItem(1)
        children = [zeta.child(j).text(0) for j in range(zeta.childCount())]
        self.assertEqual(children, ["a-model", "b-model"])

    def test_copy_paste_model(self):
        self.panel._find_and_select_model("alpha", "m1")
        self.panel.stack.setCurrentIndex(1)
        self.panel.copy_model()
        self.assertIsNotNone(self.panel._clipboard_model)
        # paste into zeta
        self.panel._find_and_select_provider("zeta")
        self.panel._selected_model = None
        self.panel.paste_model()  # QInputDialog patched -> cancelled, no crash
        # verify clipboard preserved source
        self.assertEqual(self.panel._clipboard_model.get("name"), "M1")

    def test_undo_redo(self):
        from app.main_window import MainWindow

        win = MainWindow(self.cfg)  # pushes baseline snapshot
        self.cfg.data["provider"]["alpha"]["models"]["m1"]["name"] = "CHANGED"
        win._on_data_changed()  # push changed state
        self.assertEqual(self.cfg.data["provider"]["alpha"]["models"]["m1"]["name"], "CHANGED")
        win.undo()
        self.assertEqual(self.cfg.data["provider"]["alpha"]["models"]["m1"]["name"], "M1")
        win.redo()
        self.assertEqual(self.cfg.data["provider"]["alpha"]["models"]["m1"]["name"], "CHANGED")
        win.close()

    def test_offline_schema_cache(self):
        from app.config_model import ConfigModel as CM

        # write a fake cache file at the real cache path
        cache = CM._schema_cache_path()
        os.makedirs(os.path.dirname(cache), exist_ok=True)
        with open(cache, "w", encoding="utf-8") as fh:
            json.dump({"type": "object"}, fh)
        # network fails -> fallback to cache
        from unittest import mock
        import requests as rq

        def _boom(url, **kw):
            raise rq.ConnectionError("offline")

        with mock.patch("app.config_model.requests.get", side_effect=_boom):
            result = CM.fetch_schema(timeout=1)
        self.assertEqual(result, {"type": "object"})
        os.remove(cache)


class TestProbeModelUi(unittest.TestCase):
    """_probe_fill_form fills BOTH JSON boxes (options + extra) from probe results."""

    def setUp(self):
        _app()
        _patch_message_boxes()
        self.cfg = ConfigModel(data={
            "provider": {
                "inferx": {
                    "options": {"baseURL": "https://model.inferx.net/endpoints/v1"},
                    "models": {
                        "qwen38-flash-next": {
                            # stale values that probe should overwrite/remove
                            "options": {"image": True, "reasoning_effort": "max", "stale_key": 1},
                            "interleaved": {"field": "old_field"},
                        }
                    },
                }
            }
        })
        self.panel = ProviderPanel(self.cfg)
        self.panel._find_and_select_model("inferx", "qwen38-flash-next")
        self.panel.stack.setCurrentIndex(1)
        self.panel._probe_meta = ("inferx", "qwen38-flash-next")

    def _run_probe(self, fake_result):
        self.panel._probe_fill_form(fake_result)

    def test_fills_both_json_boxes(self):
        fake = {
            "ok": True, "message": "ok",
            "max_tokens": 262000, "reasoning_field": "reasoning_content",
            "reasoning_effort": "low", "tool_call": True, "image_support": True,
        }
        self._run_probe(fake)
        import json as _json

        opts = _json.loads(self.panel.m_options.toPlainText())
        self.assertEqual(opts["reasoning_effort"], "low")
        self.assertEqual(opts["image"], True)
        self.assertEqual(opts["stale_key"], 1)  # existing non-probe keys kept
        extra = _json.loads(self.panel.m_extra.toPlainText())
        self.assertEqual(extra["interleaved"], {"field": "reasoning_content"})
        self.assertEqual(self.panel.m_output.value(), 262000)
        self.assertTrue(self.panel.m_tool_call.isChecked())
        self.assertTrue(self.panel.m_reasoning.isChecked())

    def test_removes_stale_when_not_supported(self):
        fake = {
            "ok": True, "message": "ok",
            "max_tokens": None, "reasoning_field": None,
            "reasoning_effort": None, "tool_call": False, "image_support": False,
        }
        self._run_probe(fake)
        import json as _json

        opts = _json.loads(self.panel.m_options.toPlainText())
        self.assertNotIn("reasoning_effort", opts)  # stale removed
        self.assertNotIn("image", opts)             # stale removed
        self.assertEqual(opts["stale_key"], 1)      # unrelated kept
        extra = self.panel.m_extra.toPlainText().strip()
        self.assertEqual(extra, "")                 # stale interleaved removed
        self.assertFalse(self.panel.m_tool_call.isChecked())


class TestProbeModelCallbacks(unittest.TestCase):
    """probe_model() reports steps via progress_cb and aborts via cancel_check."""

    def _fake_resp(self, code=200):
        from unittest import mock

        resp = mock.Mock()
        resp.status_code = code
        resp.json.return_value = {"data": [{"id": "m"}]}
        resp.iter_lines.return_value = []
        return resp

    def test_progress_reports_each_step(self):
        from unittest import mock
        from app import model_probe

        steps: list[str] = []
        with mock.patch("app.model_probe.requests.post", return_value=self._fake_resp()), \
             mock.patch("app.model_probe.requests.get", return_value=self._fake_resp()):
            res = model_probe.probe_model(
                "http://127.0.0.1:9/", "", "m", context=100000,
                progress_cb=steps.append,
            )
        self.assertTrue(res["ok"])
        joined = "\n".join(steps)
        self.assertIn("หา max_tokens", joined)
        self.assertIn("reasoning field", joined)
        self.assertIn("reasoning_effort", joined)
        self.assertIn("tool_call", joined)
        self.assertIn("vision", joined)
        self.assertGreaterEqual(len(steps), 5)

    def test_cancel_aborts_early(self):
        from unittest import mock
        from app import model_probe

        with mock.patch("app.model_probe.requests.post", return_value=self._fake_resp()):
            res = model_probe.probe_model(
                "http://127.0.0.1:9/", "", "m", context=100000,
                cancel_check=lambda: True,
            )
        self.assertTrue(res.get("cancelled"))
        self.assertIn("ถูกยกเลิก", res["message"])

    def test_find_max_tokens_survives_one_error(self):
        """A single timeout mid-search must not abort the whole binary search."""
        from unittest import mock
        from app import model_probe

        calls = {"n": 0}

        def _flaky(url, **kw):
            calls["n"] += 1
            if calls["n"] == 1:
                import requests as rq
                raise rq.ConnectionError("test timeout")
            return self._fake_resp(200)

        with mock.patch("app.model_probe.requests.post", side_effect=_flaky):
            res = model_probe.find_max_tokens("http://127.0.0.1:9/", "", "m", context=100000)
        self.assertTrue(res["ok"])
        self.assertGreater(res["max_tokens"], 0)
        self.assertGreaterEqual(calls["n"], 2)  # kept searching after the error

    def test_tool_call_sends_force_prompt(self):
        """test_tool_call must instruct the model to call the tool (avoid false negative)."""
        from unittest import mock
        from app import model_probe

        sent = {}

        def _capture(url, **kw):
            sent["body"] = kw.get("json")
            return self._fake_resp(200)

        with mock.patch("app.model_probe.requests.post", side_effect=_capture):
            res = model_probe.test_tool_call("http://127.0.0.1:9/", "", "m")
        self.assertTrue(res["ok"])
        body = sent["body"]
        roles = [m["role"] for m in body["messages"]]
        self.assertIn("system", roles)
        self.assertIn("tools", body)
        joined = " ".join(m["content"] for m in body["messages"])
        self.assertIn("get_time", joined)


class TestMaskSecrets(unittest.TestCase):
    def test_api_key_masked(self):
        data = {"provider": {"p": {"options": {"apiKey": "secret123", "baseURL": "https://x"}}}}
        m = mask_secrets(data)
        self.assertEqual(m["provider"]["p"]["options"]["apiKey"], "***")
        self.assertEqual(m["provider"]["p"]["options"]["baseURL"], "https://x")

    def test_headers_masked(self):
        data = {"mcp": {"s": {"headers": {"Authorization": "Bearer abc"}}}}
        m = mask_secrets(data)
        self.assertEqual(m["mcp"]["s"]["headers"]["Authorization"], "***")

    def test_non_secret_untouched(self):
        data = {"model": "a/b", "mcp": {"s": {"env": {"X64DBG_PATH": "D:\\x64dbg.exe"}}}}
        m = mask_secrets(data)
        self.assertEqual(m["model"], "a/b")
        # "X64DBG_PATH" is not a secret key name, stays as-is
        self.assertEqual(m["mcp"]["s"]["env"]["X64DBG_PATH"], "D:\\x64dbg.exe")


if __name__ == "__main__":
    unittest.main(verbosity=2)
