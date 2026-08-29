# AGENTS.md — กฎสำหรับ AI agent ที่แก้โค้ดในโปรเจกต์นี้

## เป้าหมายโปรเจกต์

GUI («opencode-config-editor») สำหรับเปิด–แก้ไข `opencode.json` (ของ `opencode desktop`) แทนการเปิดไฟล์ JSON ดิบ ๆ กำหนดจุดเจ็บ: คอนฟิกมี `provider → model → cost/limit/options` ซ้อนกันลึก และมี `mcp` อีกชุด — อยากได้ form-based UI ให้เห็น/แก้ได้โดยไม่ต้องงม nested JSON

## สแต็กที่ล็อก (เปลี่ยนไม่ได้)

- **ภาษา**: Python 3.11+
- **GUI framework**: PySide6 (Qt for Python) — **ห้ามใช้ Tkinter / Electron / Tauri / C# WinForms**
- **Validation**: `jsonschema` (Draft 2020-12) + `requests` สำหรับดาวน์โหลด schema
- **ห้ามใช้** (definitely): `npm`, `node`, ไปจนถึง WebUI (แอปนี้เป็น desktop GUI ล้วน ไม่มี frontend)

## เช็กลิสต์ฟีเจอร์

- [x] โหลด/เปิด `opencode.json` (path ปกติ + เลือกไฟล์เอง)
- [x] แก้ provider (npm, name, baseURL, apiKey, whitelist)
- [x] เพิ่ม/ลบ provider
- [x] แก้ model (id, name, reasoning, tool_call, limit.context/output, cost.*, options)
- [x] เพิ่ม/ลบ model ภายใน provider
- [x] แก้ mcp server (type local/remote, command, url, headers, environment/ env)
- [x] เพิ่ม/ลบ mcp server
- [x] บันทึก (เขียน indent=2, preserve `$schema`, preserve key `env`/`environment`)
- [x] ตรวจ Schema กับ `https://opencode.ai/config.json`

## โครงสร้าง

```
main.py                 # ทางเข้า GUI
app/__init__.py
app/config_model.py     # data layer: load/save/validate (ไม่ยุ่ง UI)
app/main_window.py      # หน้าต่างหลัก + toolbar + สลับมุมมอง + shortcuts
app/provider_panel.py   # แก้ provider/model/ราคา/context (+ auto-fill/test)
app/mcp_panel.py        # แก้ mcp servers
app/misc_panels.py      # agent / skill / permission
app/global_panel.py     # model/small_model/instructions/compaction/whitelist/blacklist
app/preview_panel.py    # live JSON preview + mask secrets
app/model_registry.py   # auto-fill จาก models.dev + ทดสอบ API
app/styles.py           # theme QSS + ฟอนต์ + QSettings
test_smoke.py           # smoke test (offscreen)
test_roundtrip.py       # unit test (38 cases)
test_functional.py      # e2e test ขับ widgets จริง
run.bat                 # double-click เปิดแอป
build.bat               # double-click บิลด์ exe
opencode_editor.spec    # PyInstaller spec (onefile + windowed + icon)
assets/opencode.ico     # ไอคอน opencode (ทางการ)
```

## คำสั่งหลัก

```
run.bat                                 # เปิดแอป (ใช้ venv อัตโนมัติ)
build.bat                               # บิลด์ exe (build.bat --clean เพื่อลบก่อน)
.venv\Scripts\python.exe main.py        # รันตรง
.venv\Scripts\python.exe test_roundtrip.py   # unit test (38)
.venv\Scripts\python.exe test_functional.py <copy-config>  # e2e
.venv\Scripts\python.exe test_smoke.py  # smoke test (ใช้ copy)
.venv\Scripts\pip install -r requirements.txt
```

## ข้อกำหนดบิว

ดู `docs/BUILD.md` — Python GUI → **PyInstaller `--onefile --windowed`** หรือ Nuitka; ต่อยอดเป็น service ดู `docs/DEPLOYMENT.md`

## กฎ WebUI

ไม่มี WebUI — ออกแบบเป็น desktop GUI ด้วย Qt Widgets (ไม่ใช่ QML) รองรับ dark/light ผ่าน QSS: อย่าไปสร้าง `src/webui/`

## ห้ามทำ

- ❌ ห้ามเพิ่ม npm/Node/JS ใด ๆ เข้าโปรเจกต์
- ❌ ห้ามสลับไป Tkinter/Electron/Tauri/C# WinForms
- ❌ ห้าม committ `apiKey` ของ provider ลง git (โน้มนําใช้ `{env:VAR}`)
- ❌ ห้ามเขียนทับ `opencode.json` จริงระหว่าง dev (ใช้ smoke test กับ copy)
- ❌ ห้ามให้ agent แก้ไฟล์ config ของ user โดยไม่ตั้งใจ — ตัว editor ต้องเป็นฝ่ายเขียนเองผ่าน `ConfigModel.save()`
