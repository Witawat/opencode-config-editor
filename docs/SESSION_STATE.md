# SESSION_STATE.md — สถานะโปรเจกต์ opencode-config-editor

## Objective
สร้าง GUI แก้ `opencode.json` ของ opencode desktop (Python + PySide6) ให้จัดการ
provider/model/ราคา/context/mcp ได้แบบฟอร์ม ไม่ต้องงม nested JSON

## ข้อสำคัญ (ห้ามลืม)
- **สแตกล็อก**: Python 3.11+ / PySide6 (Qt Widgets, ไม่ใช่ QML) / jsonschema / requests
- **ห้ามใช้**: npm, node, JS, Tauri, Electron, Tkinter, C# WinForms, WebUI (`src/webui/`)
- **ช่อง apiKey**: ใช้ `QLineEdit.Password` — ห้าม commit `opencode.json` จริง
- **mcp env key**: preserve ทั้ง `env` และ `environment` (ดู `mcp_panel.py` `_env_key`)
- **schema false alarm**: `model`/`small_model` custom provider + mcp ใช้ key `env`
  ถูก schema ทางการตีว่าผิด แต่ config รันได้จริง — ไม่ใช่ bug
- **ไม่ hot-reload**: หลัง save ต้อง quit แล้วเปิด opencode ใหม่

## Completed (commit: 7a87168)
- [x] init repo + commit ทั้งโค้ด+เอกสาร (22 files, 1711 insertions)
- [x] data layer load/save/validate (config_model.py)
- [x] provider/model editor (provider_panel.py)
- [x] mcp editor (mcp_panel.py) — รองรับ env/environment
- [x] main window toolbar + schema check (main_window.py)
- [x] run.bat + test_smoke.py (round-trip headless: PASS)

## Active / งานต่อยอด
- [ ] Phase 4: unit test ต่อช่อง (parse_money, schema_errors format)
- [ ] Phase 4: live JSON preview
- [ ] Phase 4: เพิ่ม tab agent / skill / permission
- [ ] Phase 5: build .exe (PyInstaller --collect-all PySide6 --onefile --windowed) — ยังไม่ทำ

## Blocked
- (ไม่มี) — venv + deps ติดตั้งแล้ว, smoke test ผ่าน

## Next Move
1. (optional) build .exe ตาม docs/BUILD.md
2. (optional) เพิ่ม unit test / tab agent+skill+permission
3. (optional) ติดตั้ง PyInstaller แล้วยิง build

## คำสั่งยืนยัน
```powershell
cd D:\MyCode\opencode-config-editor
run.bat                       # เปิด GUI
.venv\Scripts\python.exe test_smoke.py   # smoke test (PASS)
git log --oneline -1          # 7a87168
```

## เมื่อเริ่ม session ใหม่
พิมพ์ `/start` หรือ `/ต่อ` / `/resume` แล้วผมจะอ่านไฟล์นี้ต่อเลยจาก Next Move
