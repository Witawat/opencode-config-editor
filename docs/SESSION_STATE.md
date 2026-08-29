# SESSION_STATE.md — สถานะโปรเจกต์ opencode-config-editor

## Objective
สร้าง GUI แก้ `opencode.json` ของ opencode desktop (Python + PySide6) ให้จัดการ
provider/model/ราคา/context/mcp/agent/skill/permission/global ได้แบบฟอร์ม ไม่ต้องงม nested JSON

## ข้อสำคัญ (ห้ามลืม)
- **สแตกล็อก**: Python 3.11+ / PySide6 (Qt Widgets, ไม่ใช่ QML) / jsonschema / requests
- **ห้ามใช้**: npm, node, JS, Tauri, Electron, Tkinter, C# WinForms, WebUI (`src/webui/`)
- **ช่อง apiKey**: `QLineEdit.Password` + ปุ่มแสดง/ซ่อน — ห้าม commit `opencode.json` จริง
- **mcp env key**: preserve ทั้ง `env` และ `environment` (`mcp_panel.py` `_env_key`)
- **schema false alarm (known-issue)**: custom provider model enum + mcp key `env`
  ถูก schema ตีว่าผิด แต่ run ได้จริง — validate แยกกลุ่ม "เป็น known-issue" แล้ว
- **ไม่ hot-reload**: หลัง save ต้อง quit แล้วเปิด opencode ใหม่
- **commit แบบ merge**: ทุก panel ห้าม rebuild dict ทิ้ง key ที่ UI ไม่รู้จัก (`interleaved` ฯลฯ)
- **preview mask**: `mask_secrets()` ปกปิด apiKey/headers ก่อนแสดง/คัดลอก JSON
- **cost/compaction ทัชเซ็นเซอร์**: ใช้ `_orig_cost`/`_cost_edited`/`_comp_touched`
  แยก 0/"uncheck" ที่ "ไม่ได้แตะ" ออกจากค่าจริง
- **test กับ copy เสมอ**: ห้ามชี้ test ไป opencode.json จริง (มี apiKey)
- **รันเทสด้วย `-X utf8`** — console cp874 ขึ้น Thai ไม่ได้

## Completed (commit ล่าสุด: dbc6f5d — งาน Phase 4+ ยังไม่ commit)
- [x] init repo + commit ทั้งโค้ด+เอกสาร (22 files, 1711 insertions) — 7a87168
- [x] data layer load/save/validate (config_model.py)
- [x] provider/model editor + mcp editor + main window + run.bat + test_smoke.py
- [x] **bug fixes:** deep-merge กัน data loss (`interleaved`), `shlex` command,
  `validate()` commit ทุก panel, cost=0 เก็บได้, pop `id` ว่าง,
  commit ฟอร์มปัจจุบันก่อนสลับรายการ, cache schema เฉพาะที่สำเร็จ, `_shorten` error
- [x] **live JSON preview** (mask secrets) + คัดลอก JSON + dirty guard
- [x] **tabs:** Agent / Skill / Permission (`misc_panels.py`) + Global (`global_panel.py`)
  + model extra keys editor (`m_extra`)
- [x] **coverage 100%**: ทุก key ใน config จริงแสดง/แก้ได้ผ่านฟอร์ม + JSON Preview
- [x] **UI polish:** theme dark/light + ฟอนต์ 8-24pt + icon + dirty marker `*`
  + recent files + คีย์ลัด + save-as + eye apiKey + filter provider (`styles.py`)
- [x] **auto-fill + test:** ดึงค่าอัตโนมัติ (models.dev) + ทดสอบ API + ดึง whitelist
  (`model_registry.py`)
- [x] **schema validate:** แยก known-issue (4 ข้อจริงเป็น benign ทั้งหมด) + retry schema
- [x] **Phase 5:** `build.bat` + `opencode_editor.spec` + `assets/opencode.ico`
  → `dist\opencode-config-editor.exe` (48.5 MB, onefile+windowed, เปิดรอด)
- [x] **test suite:** `test_roundtrip.py` 38 cases + `test_functional.py` e2e 20 checks
  + `test_smoke.py` — ผ่านทั้งหมด

## Active / งานต่อยอด
- [ ] (optional) ตรวจ `.exe` บนเครื่องสะอาด / NSSM / shell:startup
- [ ] (optional) offline cache schema.json

## Blocked
- (ไม่มี)

## Next Move
1. **commit งานทั้งหมดที่ค้าง** (Phase 4 + UI polish + build + schema fix + autofill + docs)
2. (optional) ตรวจ `.exe` บนเครื่องสะอาดแล้วปล่อย release 0.2.0

## คำสั่งยืนยัน
```powershell
cd D:\MyCode\opencode-config-editor
run.bat                                    # เปิด GUI
build.bat                                  # บิลด์ exe
.venv\Scripts\python.exe test_roundtrip.py # unit test (38 PASS)
.venv\Scripts\python.exe test_functional.py <copy-config>   # e2e (20 PASS)
.venv\Scripts\python.exe test_smoke.py <copy-config>        # smoke (PASS)
git log --oneline -1                       # dbc6f5d (ก่อน commit ชุดใหญ่)
```

## เมื่อเริ่ม session ใหม่
พิมพ์ `/start` หรือ `/ต่อ` / `/resume` แล้วผมจะอ่านไฟล์นี้ต่อเลยจาก Next Move
