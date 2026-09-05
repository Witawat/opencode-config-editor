# CHANGELOG.md

การเปลี่ยนแปลงหลักของโปรเจกต์นี้

## [Unreleased]

### Added
- เอกสารชุดโปรเจกต์: `AGENTS.md`, `KNOWLEDGE_BASE.md`, `docs/*`, `PLAN.md`, รวมถึง `CHANGELOG.md`, `CONTRIBUTING.md`, `.gitignore`

## [0.4.0] — 2026-09-05

### Added
- ปุ่ม **"Probe ค่าจริง"** (`app/model_probe.py`) — ทำงานกับทุก OpenAI-compatible endpoint (ไม่จำกัด provider):
  หา `max_tokens` ที่ปลอดภัย (binary search), หา reasoning field (interleaved),
  ทดสอบ `reasoning_effort` (ค่าจาก models.dev registry + fallback ชุดกว้าง `none..auto`),
  ทดสอบ `tool_call`, ทดสอบ vision (`image_url`)
- `reasoning_effort_options(provider, model)` — ดึงค่าที่ registry ระบุ → probe ลองเฉพาะค่านั้น (ประหยัด request)
- Probe อัปเดตช่อง JSON ทั้งสองเอง: `options` (reasoning_effort + image) และ `extra keys` (interleaved) + **ลบค่าค้าง** เมื่อ probe บอกว่าไม่รองรับ
- Probe รันใน **QThread + QProgressDialog** — แสดงขั้นตอนสด ("หา max_tokens...", "ทดสอบ tool_call...") + ปุ่มยกเลิก → **GUI ไม่ค้าง**
- ปุ่ม "ทดสอบ model" — `GET /models` + `POST /chat/completions`

### Fixed
- probe / test model อ่าน baseURL/apiKey จาก widget ที่ว่างเมื่ออยู่ model form → อ่านจาก config โดยตรง
- `find_max_tokens`: timeout/error กลางทางไม่เลิกทั้ง binary search (ถือว่า "เกินไป" แล้วค้นต่อ); เงื่อนไขเช็ค `lo==0` (เดิม `lo==0 and hi==0`)
- `test_tool_call`: เพิ่ม system prompt บังคับให้ model เรียก tool → ลด false negative
- `reasoning_effort`: คืนค่าใช้ได้ทั้งหมด + UI แสดงตัวเลือก (default = ค่าต่ำสุด/ประหยัด)
- socket leak: `stream=True` ที่ไม่อ่าน body → `r.close()` ทุกครั้ง
- thread cleanup: `worker.deleteLater`

## [0.3.0] — 2026-08-29

### Added
- Drag-drop เรียงลำดับ model ภายใน provider (ซิงก์กลับ config อัตโนมัติ)
- Sort provider/model ตามตัวอักษรใน tree
- Copy/Paste model (ข้าม provider ได้) + ปุ่ม collapse/expand tree
- Batch edit cost/limit หลาย model พร้อมกัน
- Offline schema cache (validate ได้แม้ไม่มีเน็ต)
- Theme auto-follow system (dark/light/auto วนสลับ)
- Undo/Redo (Ctrl+Z/Y) + ปุ่ม "เทียบ diff" กับไฟล์บนดิสก์

## [0.2.0] — 2026-08-29

### Added
- แท็บ Agent / Skill / Permission (`app/misc_panels.py`) ตาม schema จริง
- แท็บ Global (`app/global_panel.py`): `model`, `small_model`, `instructions`, `compaction`, `enabled_providers` (whitelist), `disabled_providers` (blacklist)
- แท็บ JSON Preview (`app/preview_panel.py`) — แสดง config สด, mask apiKey/headers เป็น `***`; ปุ่ม "คัดลอก JSON"
- Auto-fill + tooling (`app/model_registry.py`): ปุ่ม "ดึงค่าอัตโนมัติ (models.dev)", "ทดสอบ API" (GET {baseURL}/models + เสนอเติม whitelist), "ดึง whitelist (registry)"
- UI polish (`app/styles.py`): dark/light theme, ฟอนต์ปรับ 8–24pt, recent files, icon opencode, คีย์ลัด (Ctrl+S/O/Shift+S, F5, Ctrl+Shift+V/C), dirty marker `*`, ปุ่ม "บันทึกเป็น...", ปุ่มแสดง/ซ่อน apiKey, กล่องกรอง provider
- Editor "extra keys" ใน model form (`interleaved` ฯลฯ)
- `build.bat` + `opencode_editor.spec` + `assets/opencode.ico` — บิลด์ `dist\opencode-config-editor.exe` (onefile, windowed, icon)
- `test_roundtrip.py` (38 unit tests) และ `test_functional.py` (e2e)

### Fixed
- Data loss: commit รีบิลด์ model/providers ทิ้ง key ที่ UI ไม่รู้จัก (เช่น `interleaved`) → commit แบบ merge เสมอ
- mcp command ที่ args มีช่องว่างถูกแยกผิด → ใช้ `shlex` parse/join; quote ไม่สมดุล = คงค่าเดิม
- `validate()` ไม่ commit MCP (ตรวจ schema โดยไม่รวม mcp ที่แก้) → `_commit_all()`
- cost = 0 ของ model ฟรีหายตอน save → เก็บ 0 เมื่อ key มีอยู่เดิม/ผู้ใช้แตะ
- `validate()` ข้อความ error ยาวเกิน 2000 ตัว → `_shorten()` (240 chars) + แยก known-issue (env/environment, custom provider enum) จาก error จริง
- Cache schema ที่ดาวน์โหลดผิดพลาดเป็นถาวร → cache เฉพาะที่สำเร็จ (retry ได้)
- แก้ฟอร์มแล้วสลับรายการ ≠ ข้อมูลหาย → commit ฟอร์มปัจจุบันก่อนสลับ

## [0.1.0] — 2026-08-29

### Added
- GUI editor (PySide6) สำหรับ `opencode.json` ของ opencode desktop
- Data layer `config_model.py`: load / save (indent=2) / validate กับ schema ทางการ
- `provider_panel.py`: tree + ฟอร์ม provider (npm, name, baseURL, apiKey, whitelist) / model (id, name, reasoning, tool_call, limit.context/output, cost.*, options)
- `mcp_panel.py`: list + ฟอร์ม local/remote; รองรับ key `env` และ `environment`
- `main_window.py`: toolbar เปิด/บันทึก/โหลดซ้ำ/ตรวจ Schema + mode switcher
- `run.bat` และ `test_smoke.py`

## Notes

จัดรูปแบบ commit ตาม [Conventional Commits](https://www.conventionalcommits.org/)
