# opencode-config-editor

GUI สำหรับเปิด-แก้ไข `opencode.json` (ของ opencode desktop) ให้ง่าย ไม่ต้องเปิดไฟล์ JSON ดิบ ๆ manual

สร้างด้วย **Python + PySide6** (Qt for Python) — ไม่ต้องใช้ node/npm

## ฟีเจอร์

- **Provider / Model** — เพิ่ม/ลบ provider, เพิ่ม model, แก้ `id`, display name, `reasoning`, `tool_call`, `limit` (context/output), `cost` (input/output/cache_read/cache_write), `options` (JSON), `extra keys` (เช่น `interleaved`)
- **MCP Servers** — เพิ่ม/ลบ mcp, ตั้ง `type` (local/remote), `command` (parse แบบ `shlex` กัน arg มีช่องว่าง), `url`, `headers`, `environment` (รองรับทั้ง key `env` และ `environment`)
- **Agent / Skill / Permission** — tabs เพิ่มตาม schema จริง (`agent` map, `skills.paths/urls`, `permission.[tool]` ask/allow/deny)
- **Global** — `model`, `small_model`, `instructions`, `compaction`, `enabled_providers` (whitelist), `disabled_providers` (blacklist)
- **ดึงค่าอัตโนมัติ** — ปุ่มเติม limit/cost/reasoning/tool_call จาก registry `models.dev` (`app/model_registry.py`)
- **ทดสอบ API / model / Probe ค่าจริง** — ทดสอบ `GET {baseURL}/models` + `POST /chat/completions`; Probe หา max_tokens, reasoning field (interleaved), reasoning_effort, tool_call, vision จาก API จริง (ใช้ได้ทุก OpenAI-compatible provider, `app/model_probe.py`) — รันใน QThread แสดงความคืบหน้า + ยกเลิกได้ (GUI ไม่ค้าง)
- **ตรวจ Schema** — validate กับ `https://opencode.ai/config.json` แยก known-issue (env/environment, custom provider) ออกจาก error จริง
- **JSON Preview** — ดู config เป็น JSON สด (mask apiKey/headers เป็น `***`) + ปุ่มคัดลอก JSON
- **UI polish** — dark/light/auto theme, ฟอนต์ปรับได้ 8–24pt (จำค่า QSettings), dirty marker `*`, recent files, คีย์ลัด, icon opencode
- **จัดการ model** — drag-drop เรียงลำดับ, sort อัตโนมัติ, copy/paste model, batch edit cost/limit
- **Undo/Redo** (Ctrl+Z/Y) + ปุ่ม "เทียบ diff" กับไฟล์บนดิสก์ + offline schema cache

## วิธีรัน

```powershell
run.bat
```

หรือ manual:

```powershell
python main.py [path/to/opencode.json]
```

## วิธีบิลด์ exe

```powershell
build.bat            # บิลด์ dist\opencode-config-editor.exe (onefile, windowed, icon opencode)
build.bat --clean    # ลบ build/dist ก่อน
```

## เทส

```powershell
.venv\Scripts\python.exe test_roundtrip.py    # unit test (64 cases)
.venv\Scripts\python.exe test_functional.py <copy-config>  # e2e ขับ GUI จริง
.venv\Scripts\python.exe test_smoke.py <copy-config>       # smoke round-trip
```

## โครงสร้าง

```
main.py                    # ทางเข้า (เปิด GUI)
app/__init__.py
app/config_model.py        # data layer: load/save/validate (ไม่ยุ่ง UI)
app/main_window.py         # toolbar + สลับมุมมอง + shortcuts
app/provider_panel.py      # แก้ provider / model / ราคา / context
app/mcp_panel.py           # แก้ mcp servers
app/misc_panels.py         # agent / skill / permission
app/global_panel.py        # model/small_model/instructions/compaction/whitelist/blacklist
app/preview_panel.py       # live JSON preview + mask secrets
app/model_registry.py      # auto-fill จาก models.dev + ทดสอบ API
app/model_probe.py         # Probe ค่าจริงจาก API (max_tokens/reasoning/effort/tool/vision)
app/styles.py              # themes dark/light + QSS + QSettings
test_smoke.py              # smoke test headless
test_roundtrip.py          # unit test (64)
test_functional.py         # e2e test
run.bat                    # double-click เปิดแอป
build.bat                  # double-click บิลด์ exe
opencode_editor.spec       # PyInstaller spec (onefile + windowed + icon)
assets/opencode.ico        # ไอคอน opencode (ทางการ)
```

## เอกสาร

- [AGENTS.md](AGENTS.md) — กฎสำหรับ agent (สแตก + ห้ามทำ + คำสั่ง)
- [KNOWLEDGE_BASE.md](KNOWLEDGE_BASE.md) — ความรู้ลึกก่อนโค้ด
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — สถาปัตยกรรม + data flow
- [docs/CONFIG.md](docs/CONFIG.md) — โครงสร้างคอนฟิกที่ editor จัดการ
- [docs/API.md](docs/API.md) — สเปก interface ภายนอก
- [docs/BUILD.md](docs/BUILD.md) — บิลด์ (PyInstaller / Nuitka / build.bat)
- [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) — deploy บน Windows
- [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md) — คู่มือ dev + เทส
- [docs/PLAN.md](docs/PLAN.md) — แผนพัฒนา + เช็กลิสต์
- [docs/SESSION_STATE.md](docs/SESSION_STATE.md) — สถานะล่าสุดสำหรับ session ต่อไป
- [CHANGELOG.md](CHANGELOG.md) — ประวัติการเปลี่ยน

## หมายเหตุ

- Config โหลดครั้งเดียวตอน opencode เริ่ม → หลังบันทึกต้อง quit แล้วเปิด opencode ใหม่
- `model`/`small_model` ที่เป็น custom provider มักถูก schema ทางการ flag ว่าไม่ถูกต้อง เพราะ schema มี enum เฉพาะ model ในตัว — เป็น **known-issue** (แอปแสดงเป็นกลุ่ม benign ไม่ใช่ error จริง)
- mcp ที่ใช้ key `env` (ไม่ใช่ `environment`) ก็โดน schema ปฏิเสธเช่นเดียวกัน — แต่ opencode รันได้จริง
- ทุก commit แบบ merge — key ที่ UI ไม่รู้จัก (เช่น `interleaved`, `toolbar`) ไม่หายตอนบันทึก
