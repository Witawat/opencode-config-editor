# DEVELOPMENT.md — คู่มือพัฒนาชุด

## เตรียมเครื่อง (Windows)

```powershell
cd D:\MyCode\opencode-config-editor
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

ตรวจติดตั้ง:
```powershell
.venv\Scripts\python.exe -c "import PySide6, jsonschema, requests; print('ok')"
```

## รัน 3 แบบ

| แบบ | คำสั่ง | ใช้เมื่อ |
|---|---|---|
| รันปกติ (GUI) | `run.bat` | เปิดใช้งาน |
| รันตรง (GUI) | `.venv\Scripts\python.exe main.py` | debug ทั่วไป |
| รัน headless/smoke | `.venv\Scripts\python.exe test_smoke.py` | CI / เช็ค round-trip |

> smoke test ใช้ copy ของ config เพื่อไม่ให้ทับไฟล์จริง? — `test_smoke.py` เขียนทับ path เดิม แต่ไม่แก้โครงสร้าง (เพื่อเซฟ dev ใช้ copy เสมอ) ดูหมายเหตุ

## คำสั่ง dev อื่น

```powershell
# เปิด config เพิ่มเติม
.venv\Scripts\python.exe main.py "C:\path\to\opencode.json"

# ทดสอบ data layer (ไม่เปิดหน้าจอ)
$env:QT_QPA_PLATFORM="offscreen"
.venv\Scripts\python.exe -c "from app.config_model import ConfigModel; print([*ConfigModel.load().providers])"
```

## เทส

- **Smoke test**: `test_smoke.py` — วาง offscreen platform, load config จริง, สร้าง window, commit + save + reload แล้วเทียบ keys เหมือนเดิม
- ยังขาด unit test ต่อช่อง — วางแผนใน `docs/PLAN.md` (Phase 4)

### วิธีรันเทสที่เขียนอยู่แล้ว

```powershell
.venv\Scripts\python.exe test_smoke.py
```

## ล็อก code style

- Python 3.11 typing: ใช้ `from __future__ import annotations` + type hints
- `app/` ใช้ package import ญาติ (`from .config_model import ...`)
- ไม่มี formatter/linter ล็อกใน repo (ยัง) — แนะนำ `ruff` / `black` ถ้าต้องการ
- **ห้าม** มี import จาก `node`/`npm`/web แบบใด ๆ ในโค้ด

## กฎเมื่อแก้โปรเจกต์

1. UI แยกจาก data layer — field/commit ต้องผ่าน `ConfigModel`
2. Preserve `$schema` และ `env`/`environment` เดิมตอน save
3. ห้ามแปรไฟล์ config จริงตอน dev — ใช้ `QInputDialog` และ test กับ copy
4. ใช้ `QT_QPA_PLATFORM=offscreen` ถ้าต้องเทส headless
