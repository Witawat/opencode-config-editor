# CHANGELOG.md

การเปลี่ยนแปลงหลักของโปรเจกต์นี้

## [Unreleased]

### Added
- เอกสารชุดโปรเจกต์: `AGENTS.md`, `KNOWLEDGE_BASE.md`, `docs/*`, `PLAN.md`, รวมถึง `CHANGELOG.md`, `CONTRIBUTING.md`, `.gitignore`

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
