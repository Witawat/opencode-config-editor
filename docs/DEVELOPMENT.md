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

## รันแบบ

| แบบ | คำสั่ง | ใช้เมื่อ |
|---|---|---|
| รันปกติ (GUI) | `run.bat` | เปิดใช้งาน |
| รันตรง (GUI) | `.venv\Scripts\python.exe main.py` | debug ทั่วไป |
| บิลด์ exe | `build.bat` | สร้าง `dist\opencode-config-editor.exe` |

## คำสั่ง dev อื่น

```powershell
# เปิด config เพิ่มเติม
.venv\Scripts\python.exe main.py "C:\path\to\opencode.json"

# ทดสอบ data layer (ไม่เปิดหน้าจอ)
$env:QT_QPA_PLATFORM="offscreen"
.venv\Scripts\python.exe -c "from app.config_model import ConfigModel; print([*ConfigModel.load().providers])"
```

## เทส (3 ชุด)

```powershell
.venv\Scripts\python.exe test_roundtrip.py     # unit test (64 cases)
.venv\Scripts\python.exe test_functional.py <copy-config>   # e2e ขับ GUI จริง
.venv\Scripts\python.exe test_smoke.py <copy-config>        # smoke round-trip
```

- **`test_roundtrip.py`** — unit test ตัว data layer + panel ต่าง ๆ: `parse_money`, `schema_errors` format, มัก merge กัน data loss (`interleaved`), cost=0, mcp `shlex`, env preserve, agent/skill/permission/global round-trip, `mask_secrets`
- **`test_functional.py`** — จับ real widgets: เลือก provider → เพิ่ม model → แก้ agent/skill/permission/global → save → reload → ตรวจค่า (ต้องส่ง path ของไฟล์ **copy**) ครอบดันรายงาน e2e ALL CHECKS PASSED
- **`test_smoke.py`** — build window offscreen + commit + save round-trip + เทียบคีย์ครบ

> ⚠️ ทุกเทสที่ไม่ใช่ dry-run ใช้ copy ของ config เสมอ ห้ามชี้ไป `opencode.json` จริง (มี apiKey)

## ล็อก code style

- Python 3.11 typing: ใช้ `from __future__ import annotations` + type hints
- `app/` ใช้ package import ญาติ (`from .config_model import ...`)
- data layer (`config_model.py`) ห้าม import Qt/widget ใด ๆ
- ทุก panel commit แบบ **merge** — ห้าม rebuild dict ที่ทิ้ง key ที่ UI ไม่รู้จัก
- ไม่มี formatter/linter ล็อกใน repo (ยัง) — แนะนำ `ruff` / `black` ถ้าต้องการ
- **ห้าม** มี import จาก `node`/`npm`/web แบบใด ๆ ในโค้ด

## กฎเมื่อแก้โปรเจกต์

1. UI แยกจาก data layer — field/commit ต้องผ่าน `ConfigModel`
2. Preserve `$schema` และ `env`/`environment` เดิมตอน save
3. ห้ามแปรไฟล์ config จริงตอน dev — ใช้ test กับ copy
4. ใช้ `QT_QPA_PLATFORM=offscreen` ถ้าต้องเทส headless
5. ปุ่ม/ฟีเจอร์ใหม่ ต้องมี unit test ครอบ
6. อย่าเพิ่ม dependency ใน `requirements.txt` โดยไม่จำเป็น (มีแค่ PySide6 / jsonschema / requests)
