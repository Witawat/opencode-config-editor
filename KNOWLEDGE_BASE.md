# KNOWLEDGE_BASE.md — ความรู้ลึกก่อนเขียนโค้ด

## 1. บริบท

`opencode` เป็น CLI ตัวช่วยเขียนโค้ดที่อ่าน config จาก `opencode.json` โปรเจกต์นี้คือ GUI ที่ทำให้ผู้ใช้จัดการคอนฟิกชุดนั้นได้อย่างเป็นรูปธรรม เหตุผลหลักที่จะมีตัวนี้: คอนฟิกของ opencode มี `provider` ซ้อน `models` ซ้อน `limit`/`cost`/`options` หลายระดับ และ `mcp` หลายตัว ซึ่งแก้ด้วยมือใน text editor ผิดง่ายมาก

## 2. ทำไมต้อง PySide6

- ต้องการ desktop GUI หนึ่งหน้าต่าง + form ให้เครื่องมือที่ user ใช้จริง
- PySide6 เป็น Qt binding ทางการ ให้ widget ครบ (`QTreeWidget`, `QFormLayout`, `QComboBox`, `QDoubleSpinBox` ฯลฯ) และติดตั้ง/รันบน Windows ได้ตรง ๆ ด้วย Python ที่ user มีอยู่แล้ว (3.11)
- ต่างจาก Tauri (ต้อง node + Rust toolchain) และ Electron (ต้อง node) — ที่นี่ไม่ต้องมี node เลย ซึ่งตรงกับ "ห้าม npm" ของโปรเจกต์

## 3. สถาปัตยกรรมรันไทม์

แยกเป็นสองชั้นชัดเจน:
- **Data layer** (`config_model.py`) — pure dict/list, รับผิดชอบโหลด/บันทึก/validate เท่านั้น ไม่รู้จัก widget
- **UI layer** (`main_window.py`, `provider_panel.py`, `mcp_panel.py`) — จัดการ widget, อ่าน/เขียนค่าผ่าน `ConfigModel`, เรียก `commit()` ก่อน `save()`

นี้สำคัญเพราะ schema validation และ save ต้องเป็นอิสระจาก GUI เพื่อทดสอบ headless ได้

## 4. โมดูล

| โมดูล | หน้าที่ |
|---|---|
| `config_model.py` | `load()`, `save()`, `schema_errors()` (+`_shorten`), `fetch_schema()`, `providers`, `mcp`, `parse_money` |
| `main_window.py` | `MainWindow`: toolbar, mode switcher, `open/save/save_as/reload/validate`, recent files, shortcuts, dirty guard |
| `provider_panel.py` | tree provider/model + ฟอร์ม provider + ฟอร์ม model (+ filters, ฟอร์ม extra keys, autofill/test buttons) |
| `mcp_panel.py` | list mcp + ฟอร์ม local/remote (command ด้วย `shlex`) |
| `misc_panels.py` | agent / skill / permission panels |
| `global_panel.py` | top-level: model/small_model/instructions/compaction/whitelist/blacklist |
| `preview_panel.py` | live JSON + `mask_secrets()` (apiKey/headers → `***`) |
| `model_registry.py` | ดึง models.dev + find/search model + `test_provider_api` + `check_mcp_command` |
| `styles.py` | themes dark/light QSS + font size + QSettings (`remember()`/`load_recent()`) |
| `test_roundtrip.py` | unit test (38) |
| `test_functional.py` | e2e ขับ widgets จริง |

## 5. Config: รากฐานข้อมูล

ทั้งแอปหมุนรอบ dict ตัวเดียว `config.data` ซึ่งเป็นสิ่งที่ `json.load` ตรงจาก `opencode.json` ได้ ไม่มี DB — save คือเขียน JSON กลับ `indent=2, ensure_ascii=False`

**ความระวัง:**
- `model` / `small_model` เป็น string `provider/model-id` (เช่น `inferx/deepseek-v4-flash-0731`)
- `skills` เป็น object (`paths`/`urls`) ไม่ใช่ array
- `agent` เป็น object keyed-by-name
- `plugin` เป็น array
- `mcp[name].command` เป็น array ไม่ใช่ string; `type` จำเป็น
- `permission` เป็น string หรือ object keyed-by-tool
- schema `McpLocalConfig` อนุญาต `environment` เท่านั้น (ไม่รวม `env`, additionalProps false) → key `env` โดน flag — แต่ opencode รันได้จริง (known-issue)

## 6. API

ไม่มี HTTP endpoint ภายใน แต่ติดต่อ external 2 ตัว:
- `https://opencode.ai/config.json` — schema (validate)
- `https://models.dev/api.json` — registry (auto-fill limit/cost/reasoning + whitelist) — ดู `docs/API.md`

## 7. กับดักบิว

- **PyInstaller** ต้อง bundle PySide6: ใช้ `opencode_editor.spec` (`--collect-all PySide6` อยู่ใน hint ของ build.bat) หรือ `--collect-binaries PySide6` มิฉะนั้นแอปเปิดมาเ้ด่นรายงาน error หา plugin แพลตฟอร์ม
- **QDoubleSpinBox** ไม่เก็บข้อความ — ถ้า user ต้องการราคา "0.007" ต้องตั้ง `decimals=4` (ตั้งแล้ว)
- **env vs environment**: config ของ opencode ในป่าใช้ทั้ง `env` และ `environment` สำหรับ mcp; editor ต้อง preserve key เดิม (ดู `mcp_panel.py` `_env_key`)
- **cost 0 (model ฟรี)**: QDoubleSpinBox default 0 — save จะทิ้ง 0 ที่ "ไม่ได้แตะ" แต่เก็บ 0 เมื่อ key มีอยู่เดิมหรือ user แก้จริง (ดู `_orig_cost`/`_cost_edited`)
- **checkbox compaction**: เขียนเฉพาะเมื่อ user แตะจริง (uncheck = pop key) — ใช้ `_comp_touched` เช่นเดียวกับ cost
- **offscreen test**: ตั้ง `QT_QPA_PLATFORM=offscreen` เพื่อรัน GUI ใน CI/headless
- **QMessageBox/QInputDialog บล็อกใน offscreen**: test ต้อง `mock.patch` ก่อนเรียก
- **console encoding (cp874)**: รันเทสด้วย `-X utf8` เพื่อไม่ให้ส่ง error Thai

## 8. ความปลอดภัย

- apiKey ของ provider เก็บ plaintext ใน `opencode.json` อยู่แล้ว — **editor ต้องไม่เผลอแสดงเป็นข้อความโล่ง** → use `QLineEdit.Password` สำหรับช่อง apiKey
- ห้าม committ `opencode.json` จริงหรือ apiKey ลง git
- การ validate ไม่ควร ดาวน์โหลด schema เมื่อ offline — `fetch_schema()` คืน `{}` ให้ caller จัดการ

## 9. เทส

- `test_roundtrip.py` — 38 unit tests (parse_money, schema_errors format+shorten, merge กัน data loss, cost 0, shlex, env preserve, agent/skill/permission/global, mask_secrets, registry pure-logic)
- `test_functional.py` — e2e ขับ widget จริง (20 checks)
- `test_smoke.py` — offscreen round-trip เทียบคีย์ครบ

## 10. Roadmap

ดู `docs/PLAN.md` — v1 ครอบ provider/model/ราคา/context/mcp; v2+: agent/skill/permission + live preview + global + auto-fill + UI polish (เสร็จแล้วทั้งหมด); เหลือ: ตรวจ `.exe` เครื่องสะอาด, NSSM/shell:startup
