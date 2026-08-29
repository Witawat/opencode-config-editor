# ARCHITECTURE.md — สถาปัตยกรรมซอฟต์แวร์

## ภาพรวม

แอปเป็น **two-layer** desktop GUI (PySide6):

```
+----------------------------- MainWindow ------------------------------+
| toolbar: เปิด | บันทึก | โหลดซ้ำ | path_label | ตรวจ Schema               |
+------------------------------------------------------------------------+
| mode_sel [Provider/Model | MCP Servers]                                  |
|                       QStackedWidget                                      |
|    +----------------+        +-----------------+                         |
|    | ProviderPanel  |        | MCPPanel        |                         |
|    | (tree + form)  |        | (list + form)   |                         |
|    +--------+-------+        +--------+--------+                         |
|             |                          |                                |
|         QFormLayout                  QFormLayout                         |
+-------------+----------------------------+------------------------------+
              |  commit() / set_config()              |
              v                                    v
            ConfigModel  ------------------------->  ConfigModel.data
             (data layer)                            (dict/json)
                 |  save() / load() / schema_errors()
                 v
          opencode.json  <-->  https://opencode.ai/config.json
```

## สถาปัตยกรรมรันไทม์

- **ทางเข้า**: `main.py` → สร้าง `QApplication` → `ConfigModel.load(path)` (fallback เป็น dict ว่างถ้าไฟล์เพี้ยน) → `MainWindow(config)` → `app.exec()`
- **การแยก**: `config_model.py` ไม่นำเข้า widget ใด (มีแต่ `dataclass`, `jsonschema`, `requests`) → ทดสอบได้แบบ offscreen
- **การไหลของข้อมูล (data flow)**:
  1. เปิดแอป → `load()` → `config.data` (dict) → `ProviderPanel`/`MCPPanel` อ่าน fill ลงฟอร์ม
  2. User แก้ฟอร์ม → ยังไม่เขียนกลับทันที
  3. กด **บันทึก** → `MainWindow.save()` → `nav.commit()` + `mcp_tab.commit()` เขียนค่าฟอร์มลง `config.data` → `config.save()` เขียนไฟล์

## โมดูลและ responsi­bility

| ไฟล์ | รับผิดชอบ | ไม่ยุ่งกับ |
|---|---|---|
| `app/config_model.py` | load/save/validate, providers/mcp accessors | widget |
| `app/main_window.py` | toolbar, mode switch, orchestrate save/validate | field detail |
| `app/provider_panel.py` | tree provider/model + 2 ฟอร์ม (provider, model) | ไฟล์ IO ตรง |
| `app/mcp_panel.py` | list mcp + ฟอร์ม local/remote | ไฟล์ IO ตรง |
| `test_smoke.py` | round-trip headless | GUI แสดงผลจริง |

## Request flow (คือ event flow ของ GUI)

```
[User] กด "บันทึก"
  └─ MainWindow.save()
       ├─ nav.commit()      → pull ฟอร์ม provider/model ปัจจุบันลง config.data
       ├─ mcp_tab.commit()  → pull ฟอร์ม mcp ปัจจุบันลง config.data
       └─ config.save()     → json.dump(config.data, indent=2, ensure_ascii=False)
```

```
[User] กด "ตรวจ Schema"
  └─ MainWindow.validate()
       ├─ nav.commit() (sync ล่าสุด)
       ├─ ConfigModel.fetch_schema() via requests
       └─ config.schema_errors(schema) → แจ้งผล
```

## จุดสำคัญ / ข้อจำกัด

- **ไม่ hot-reload**: `opencode.json` โหลดครั้งเดียวเมื่อ opencode เริ่ม — หลัง save ต้อง quit แล้วเปิดใหม่
- **independent layer**: UI ต้องไม่รู้ schema โดยตรง — ขอ schema ผ่าน `ConfigModel.fetch_schema()` เสมอ
- **preserve key**: mcp ใช้ key `env` หรือ `environment` — commit รักษาตัวเดิม (`mcp_panel._env_key`)
- **API key**: ช่อง apiKey ใช้ `QLineEdit.Password` ไม่แสดงข้อความโล่ง
- **gitignore**: ไม่ commit `opencode.json` ของ user, dist, `.venv`

## แผนต่อยอด

ดู `docs/PLAN.md` — เพิ่ม tab `agent`/`skill`/`permission`, live JSON preview, ตั้งราคาแบบสร้างอัตโนมัติ
