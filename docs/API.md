# API.md — สเปกของ interface ภายนอก

## บทนำ

แอปนี้เป็น desktop GUI ไม่มี HTTP server ภายใน แต่ติดต่อกับ **external JSON Schema** หนึ่งตัว และมี **โปรแกรมสำคัญ** ที่คงเส้นคงวาในรูปแบบของฟังก์ชัน

## External: JSON Schema ของ opencode

- **URL**: `https://opencode.ai/config.json`
- **เข้าใช้**: `ConfigModel.fetch_schema()` — ใช้ `requests` GET
- **ผลตอบ**: `dict` ถ้าสำเร็จ, `{}` ถ้า offline/error
- **ผู้เรียก**: `MainWindow.validate()` ผ่าน `ConfigModel.schema_errors(schema)`

```
GET https://opencode.ai/config.json
200 OK
Content-Type: application/json
```
ใช้สำหรับ validate `config.data` ตาม Draft 2020-12

## External: models.dev registry

- **URL**: `https://models.dev/api.json`
- **เข้าใช้**: `app/model_registry.fetch_registry()` (cached ต่อ session)
- **ผู้เรียก**: ปุ่ม "ดึงค่าอัตโนมัติ (models.dev)" / "ดึง whitelist (registry)"
- ใช้สนับสนุนรู้ขึ้นอยู่ว่ามี key อะไรบ้าง (limit/cost/reasoning/tool_call/interleaved)

## Interface "ฟอร์ม" (contract ที่ UI พึ่งพา)

### `ConfigModel`

| สมาชิก | signature | ใช้ทำอะไร |
|---|---|---|
| `load(path)` | classmethod → `ConfigModel` | เปิดไฟล์ JSON |
| `save(path=None)` | `-> None` | เขียน JSON กลับ (`indent=2, ensure_ascii=False`) |
| `schema_errors(schema)` | `-> list[str]` | คืนข้อความ error ของ validation (ย่อข้อความยาวด้วย `_shorten`) |
| `fetch_schema()` | staticmethod → `dict` | ดึง schema จากเน็ต |
| `providers` | property → `dict` | map ของ provider (สร้าง key ให้ถ้าขาด) |
| `provider(name)` | `-> dict \| None` | เอา provider ตัวเดียว |
| `add_provider(name)`, `remove_provider(name)` | `-> dict` / `-> None` | เพิ่ม/ลบ provider |
| `mcp` | property → `dict` | map ของ mcp servers |
| `DEFAULT_CONFIG_PATH` | class const | path ปกติของ global config |

### `MainWindow`

| method | หน้าที่ |
|---|---|
| `open_file()` | `QFileDialog` เลือก `opencode.json` |
| `load_from(path)` | reload ลง panels |
| `save()` | `_commit_all()` + `config.save()` |
| `save_as()` | เลือก path ใหม่ + save |
| `validate()` | fetch schema + รายงาน errors (แบ่ง known-issue) |
| `reload()` | `load_from(config.path)` |
| `copy_json()` | คัดลอก JSON (mask secret) ไปคลิปบอร์ด |
| `toggle_theme()` / `set_font_size(n)` | สลับธีม / เปลี่ยนฟอนต์ + QSettings |

### Panels (provider / mcp / agent / skill / permission / global)

| method | หน้าที่ |
|---|---|
| `set_config(config)` | ชี้ config ใหม่แล้ว populate |
| `commit()` | เขียนค่าฟอร์มปัจจุบันลง `config.data` (แบบ merge — ไม่ทิ้ง key ที่ UI ไม่รู้จัก) |
| `data_changed` (signal) | แจ้ง main ว่าเพิ่งแก้ (dirty status) |

### `model_registry`

| method | หน้าที่ |
|---|---|
| `fetch_registry(timeout, force)` | ดึง models.dev (cache) `{}` นอกสำเร็จ |
| `find_model_info(provider, model_key)` | ค้น model ใน registry (exact / suffix) → dict หรือ None |
| `search_models(provider, pattern)` | รายการ model id ของ provider (สำหรับ whitelist) |
| `test_provider_api(base_url, api_key)` | `GET {baseURL}/models` → `{ok, message, models?}` |
| `check_mcp_command(command)` | ตรวจ executable ตัวแรกใน PATH |

### `preview_panel` / `styles`

| method | หน้าที่ |
|---|---|
| `mask_secrets(data)` | deep copy แทน `apiKey`/`Bearer`/`token` → `***` |
| `PreviewPanel.refresh()` | เรนเดอร์ JSON ปัจจุบัน |
| `apply_theme(app, theme, font_size)` | ใช้ QSS + ขนาดฟอนต์ |
| `remember(window)` / `load_recent()` | จำ geometry/theme/font/recent ใน QSettings |

## Error format

- Validation error : `"path/to/field: message"` เรียงตาม `err.path` — ข้อความยาวถูกย่อ (`_shorten`, 240 chars)
- เปิดไฟล์เพี้ยน : ยก exception → `QMessageBox.critical`
- Offline schema : คืน `{}` → `QMessageBox.warning` (บอกให้เช็คเน็ต) — cache เฉพาะที่สำเร็จ (retry ได้)
- Bad JSON ในช่อง options/headers/env/extra keys : `QMessageBox.warning` (โต้ยง ไม่บันทึกช่องนั้น)
- **known-issue** (env/environment, custom provider enum): แสดงกลุ่มแยก "เป็น known-issue" — ไม่บล็อก save

## อัตลักษณ์ (identity) ของโปรแกรม

- **ชื่อแอป**: `opencode-config-editor`
- **entry**: `python main.py [path]`
- **ใช้ run.bat**: double-click เรียก venv แล้วเปิด main.py
- **ใช้ build.bat**: double-click บิลด์ `dist\opencode-config-editor.exe`

## หมายเหตุ

- ไม่มี auth ภายใน เพราะเป็น local tool
- ไม่มี rate-limit เพราะเป็น desktop app
- UI setting (theme/ฟอนต์/path ล่าสุด/recent files) เก็บใน QSettings ไม่เขียนทับ opencode.json
