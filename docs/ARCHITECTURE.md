# ARCHITECTURE.md — สถาปัตยกรรมซอฟต์แวร์

## ภาพรวม

แอปเป็น **two-layer** desktop GUI (PySide6):

```
+----------------------------- MainWindow ------------------------------+
| toolbar: เปิด | บันทึก | โหลดซ้ำ | บันทึกเป็น | path | ตรวจ Schema     |
|          คัดลอก JSON | ธีม | ฟอนต์(8-24pt) | เปิดล่าสุด                |
+------------------------------------------------------------------------+
| mode_sel [Provider/Model | MCP | Agent | Skill | Permission | Global | JSON Preview]
|                       QStackedWidget                                   |
|   +----------+  +----------+  +--------+  +-------+  +--------+  +---+
|   | Provider |  |  MCP     |  | Agent  |  | Skill |  | Perm   |  | J |
|   | Panel    |  |  Panel   |  | Panel  |  | Panel |  | Panel  |  | S |
|   +----------+  +----------+  +--------+  +-------+  +--------+  +---+
| + Global Panel (model/small_model/instructions/compaction/wl/bl) +
+------------------------------------------------------------------------+
         _commit_all()  (ทุก panel commit แบบ merge -> ไม่ทิ้ง key ที่ UI ไม่รู้จัก)
         v
      ConfigModel  --------------------------------->  ConfigModel.data
      (data layer)        save()/load()/schema_errors()      (dict/json)
         |        +---------------  network -------------+
         |        v                                      v
         |   https://opencode.ai/config.json    https://models.dev/api.json
         |        (validate)                    (auto-fill limit/cost, whitelist)
         v                                
   opencode.json
   PreviewPanel (mask secrets)  <-- _commit_all + refresh
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
| `app/main_window.py` | toolbar, mode switch, orchestrate save/validate/dirty guard | field detail |
| `app/provider_panel.py` | tree provider/model + 2 ฟอร์ม (provider, model) | ไฟล์ IO ตรง |
| `app/mcp_panel.py` | list mcp + ฟอร์ม local/remote (shlex command) | ไฟล์ IO ตรง |
| `app/misc_panels.py` | agent / skill / permission panels | ไฟล์ IO ตรง |
| `app/global_panel.py` | top-level: model/small_model/instructions/compaction/whitelist/blacklist | ไฟล์ IO ตรง |
| `app/preview_panel.py` | live JSON + mask_secrets (apiKey/headers -> ***) | การเขียนไฟล์ |
| `test_smoke.py` | round-trip headless | GUI แสดงผลจริง |
| `test_roundtrip.py` | unit test (22 cases) ครอบ bug round-trip | GUI แสดงผลจริง |

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
- **commit แบบ merge**: ทุก panel merge เฉพาะ field ที่รู้จัก — ไม่ rebuild dict ทิ้ง key ที่ UI ไม่รู้จัก (`interleaved`, `toolbar`, ฯลฯ)
- **preserve key**: mcp ใช้ key `env` หรือ `environment` — commit รักษาตัวเดิม (`mcp_panel._env_key`)
- **API key**: ช่อง apiKey ใช้ `QLineEdit.Password`; preview/คัดลอก JSON ผ่าน `mask_secrets()` แทนเป็น `***`
- **dirty guard**: MainWindow จำ `_dirty` — เตือนก่อน reload/เปิดไฟล์ใหม่/ปิดโดยไม่บันทึก + `*` ใน title
- **UI settings**: theme/ฟอนต์/geometry/recent อยู่ใน QSettings (`app/styles.py`) — ไม่แตะ opencode.json
- **touch-sensitive write**: cost 0 และ compaction boolean เขียนเฉพาะเมื่อ key มีเดิมหรือ user แตะจริง (`_orig_cost`/`_cost_edited`/`_comp_touched`)
- **known-issue**: schema flag custom provider model (enum models.dev) + mcp key `env` — validate แยกกลุ่ม benign/known-issue
- **gitignore**: ไม่ commit `opencode.json` ของ user, dist, `.venv`, `*.spec` (spec `opencode_editor.spec` อยู่ใน repo เดี๋ยวนี้? — ดู gitignore: `*.spec` ถูก ignore → ไฟล์ในเครื่อง แต่ไม่ commit)

## แผนต่อยอด

ดู `docs/PLAN.md` — Phase 5: build .exe (PyInstaller `--onefile --windowed`), ตั้งราคาแบบสร้างอัตโนมัติ
