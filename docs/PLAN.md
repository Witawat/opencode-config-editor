# PLAN.md — แผนพัฒนา 5 เฟส + เช็กลิสต์

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

## Phase 3 — WebUI/API

- [x] ไม่มี WebUI — แทนด้วย desktop GUI (PySide6)
- [x] mode switcher ระหว่าง Provider/Model ↔ MCP

## Phase 4 — เสริม (ค่าถูกต้อง / UX)

- [ ] unit test ต่อช่อง: cost parse (`parse_money`), `schema_errors` format
- [ ] live JSON preview (แสดง config หลังแก้)
- [ ] เพิ่ม tab `agent` / `skill` / `permission`
- [ ] ปุ่ม "คัดลอก JSON" / "เปิดล่าสุด"

## Phase 5 — Build / Service

- [x] `run.bat` double-click
- [ ] PyInstaller `--collect-all PySide6 --onefile --windowed`
- [ ] ตรวจ `.exe` บนเครื่องสะอาด
- [ ] (ทางเลือก) NSSM / shell:startup

## เช็กลิสต์ความพร้อม (check-docs)

- [x] ไฟล์ `.md` ลิงก์กันครบ: `README` ⟷ `AGENTS` ⟷ `KNOWLEDGE_BASE` ⟷ `docs/*`
- [x] ไม่มี stack หลง (Node/Java) — ตรวจ `grep -ri "node\|java"` เหลือแต่ "ห้ามใช้"
- [x] Build/Deploy ปรับเป็น Python + PySide6
- [ ] เทส unit เก็บม้วนได้ (Phase 4)
