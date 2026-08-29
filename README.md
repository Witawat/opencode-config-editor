# opencode-config-editor

GUI สำหรับเปิด-แก้ไข `opencode.json` (ของ opencode desktop) ให้ง่าย ไม่ต้องเปิดไฟล์ JSON ดิบ ๆ manual

สร้างด้วย **Python + PySide6** (Qt for Python) — ไม่ต้องใช้ node/npm

## ฟีเจอร์

- **Provider / Model** — เพิ่ม/ลบ provider, เพิ่ม model, แก้ `id`, display name, `reasoning`, `tool_call`, `limit` (context/output), `cost` (input/output/cache_read/cache_write), `options` (JSON)
- **MCP Servers** — เพิ่ม/ลบ mcp, ตั้ง `type` (local/remote), `command`, `url`, `headers`, `environment` (รองรับทั้ง key `env` และ `environment`)
- **ตรวจ Schema** — validate กับ `https://opencode.ai/config.json`

## วิธีรัน

```powershell
run.bat
```

หรือ manual:

```powershell
python main.py [path/to/opencode.json]
```

## โครงสร้าง

```
main.py                    # ทางเข้า (เปิด GUI)
app/__init__.py
app/config_model.py        # data layer: load/save/validate (ไม่ยุ่ง UI)
app/main_window.py         # toolbar + สลับมุมมอง
app/provider_panel.py      # แก้ provider / model / ราคา / context
app/mcp_panel.py           # แก้ mcp servers
test_smoke.py              # smoke test headless
run.bat                    # double-click เปิดแอป
```

## เอกสาร

- [AGENTS.md](AGENTS.md) — กฎสำหรับ agent (สแตก + ห้ามทำ + คำสั่ง)
- [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md) — ความรู้ลึกก่อนโค้ด
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — สถาปัตยกรรม + data flow
- [docs/CONFIG.md](docs/CONFIG.md) — โครงสร้างคอนฟิกที่ editor จัดการ
- [docs/API.md](docs/API.md) — สเปก interface ภายนอก
- [docs/BUILD.md](docs/BUILD.md) — บิลด์ (PyInstaller / Nuitka)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — deploy บน Windows
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — คู่มือ dev + เทส
- [docs/PLAN.md](docs/PLAN.md) — แผน 5 เฟส + เช็กลิสต์

## หมายเหตุ

- Config โหลดครั้งเดียวตอน opencode เริ่ม → หลังบันทึกต้อง quit แล้วเปิด opencode ใหม่
- `model`/`small_model` ที่เป็น custom provider มักถูก schema ทางการ flag ว่าถูกต้อง เพราะ schema มี enum เฉพาะ model ตัวในตัว — เป็น false alarm ได้
