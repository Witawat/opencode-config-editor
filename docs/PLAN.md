# PLAN.md — แผนพัฒนา + เช็กลิสต์

## Phase 0 — Scaffold

- [x] สร้างโครง `app/`
- [x] venv + `requirements.txt` (PySide6, jsonschema, requests)
- [x] `config_model.py` data layer
- [x] `test_smoke.py` (round-trip headless)

## Phase 1 — Core (provider/model)

- [x] `provider_panel.py` tree + ฟอร์ม provider
- [x] ฟอร์ม model (`id`, name, reasoning, tool_call, limit, cost, options)
- [x] เพิ่ม/ลบ provider, model

## Phase 2 — Schema / Validation

- [x] `fetch_schema()` + `schema_errors()` (Draft 2020-12)
- [x] MainWindow button "ตรวจ Schema"
- [x] schema error message ถูกย่อ (`_shorten`) + แยก known-issue (env/environment, custom provider enum) จาก error จริง

## Phase 3 — WebUI/API

- [x] ไม่มี WebUI — แทนด้วย desktop GUI (PySide6)
- [x] mode switcher ระหว่าง Provider/Model ↔ MCP

## Phase 4 — เสริม (ค่าถูกต้อง / UX)

- [x] unit test ต่อช่อง: cost parse (`parse_money`), `schema_errors` format — `test_roundtrip.py`
- [x] live JSON preview (แสดง config หลังแก้, mask apiKey/headers)
- [x] เพิ่ม tab `agent` / `skill` / `permission` (`app/misc_panels.py`)
- [x] ปุ่ม "คัดลอก JSON" / dirty guard ก่อน reload/ปิด
- [x] bug fixes: deep-merge กัน data loss (interleaved), shlex command, validate commit mcp, cost=0, pop id
- [x] แท็บ Global: model/small_model/instructions/compaction/whitelist/blacklist (`app/global_panel.py`)
- [x] model form extra keys editor (`interleaved` ฯลฯ) — coverage 100% (audit: ทุก key ใน config จริงแสดง/แก้ได้)

## Phase 4.5 — ต่อยอด (polish + tooling)

- [x] dark/light theme QSS + ฟอนต์ปรับ 8–24pt พร้อม QSettings (`app/styles.py`)
- [x] window icon (opencode.ico) + dirty marker `*` ใน title + recent files 5 รายการ
- [x] คีย์ลัด: Ctrl+S/O/Shift+S, F5, Ctrl+Shift+V/C
- [x] ปุ่ม "บันทึกเป็น..." + ปุ่มแสดง/ซ่อน apiKey + กล่องกรอง provider
- [x] auto-fill: ปุ่ม "ดึงค่าอัตโนมัติ (models.dev)" — limit/cost/reasoning/tool_call/interleaved (`app/model_registry.py`)
- [x] ปุ่ม "ทดสอบ API" (GET {baseURL}/models) + "ดึง whitelist (registry)"

## Phase 5 — Build / Service

- [x] `run.bat` double-click
- [x] PyInstaller `--onefile --windowed --icon assets/opencode.ico` ผ่าน `opencode_editor.spec`
- [x] `build.bat` (double-click / `--clean`) — ติดตั้ง pyinstaller ให้เอง
- [x] ตรวจ `.exe` รันได้ (48.5 MB, ไม่มี console)
- [ ] ตรวจ `.exe` บนเครื่องสะอาด
- [ ] (ทางเลือก) NSSM / shell:startup

## เช็กลิสต์ความพร้อม (check-docs)

- [x] ไฟล์ `.md` ลิงก์กันครบ: `README` ⟷ `AGENTS` ⟷ `KNOWLEDGE_BASE` ⟷ `docs/*`
- [x] ไม่มี stack หลง (Node/Java) — ตรวจ `grep -ri "node\|java"` เหลือแต่ "ห้ามใช้"
- [x] Build/Deploy ปรับเป็น Python + PySide6
- [x] เทส unit เก็บม้วนได้ (`test_roundtrip.py` 38 cases + `test_functional.py` e2e + smoke)
