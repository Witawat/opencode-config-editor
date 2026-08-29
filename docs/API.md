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

## Interface "ฟอร์ม" (contract ที่ UI พึ่งพา)

### `ConfigModel`

| สมาชิก | signature | ใช้ทำอะไร |
|---|---|---|
| `load(path)` | classmethod → `ConfigModel` | เปิดไฟล์ JSON |
| `save(path=None)` | `-> None` | เขียน JSON กลับ (`indent=2, ensure_ascii=False`) |
| `schema_errors(schema)` | `-> list[str]` | คืนข้อความ error ของ validation |
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
| `save()` | commit + `config.save()` |
| `validate()` | fetch schema + รายงาน errors |
| `reload()` | `load_from(config.path)` |

### Panels (ทั้ง provider & mcp)

| method | หน้าที่ |
|---|---|
| `set_config(config)` | ชี้ config ใหม่แล้ว populate |
| `commit()` | เขียนค่าฟอร์มปัจจุบันลง `config.data` |
| `data_changed` (signal) | แจ้ง main ว่าเพิ่งแก้ (dirty status) |

## Error format

- Validation error : `"path/to/field: message"` เรียงตาม `err.path`
- เปิดไฟล์เพี้ยน : ยก exception → `QMessageBox.critical`
- Offline schema : คืน `{}` → `QMessageBox.warning` (บอกให้เช็คเน็ต)
- Bad JSON ในช่อง options/headers/env : `QMessageBox.warning` (โต้ยง ไม่บันทึกช่องนั้น)

## อัตลักษณ์ (identity) ของโปรแกรม

- **ชื่อแอป**: `opencode-config-editor`
- **entry**: `python main.py [path]`
- **ใช้ run.bat**: double-click เรียก venv แล้วเปิด main.py

## หมายเหตุ

- ไม่มี auth ภายใน เพราะเป็น local tool
- ไม่มี rate-limit เพราะเป็น desktop app
