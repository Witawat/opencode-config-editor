# KNOWLEDGE_BASE.md — ความรู้ลึกก่อนเขียนโค้ด

## 1. บริบท

`opencode` เป็น CLI ตัวช่วยเขียนโค้ดที่อ่าน config จาก `opencode.json` โปรเจกต์นี้คือ GUI ที่ทำให้ผู้ใช้จัดการคอนฟิกชุดนั้นได้อย่างเป็นรูปธรรม เหตุผลหลักที่จะมีตัวนี้: คอนฟิกของ opencode มี `provider` ซ้อน `models` ซ้อน `limit`/`cost`/`options` หลายระดับ และ `mcp` หลายตัว ซึ่งแก้ด้วยมือใน text editor ผิดง่ายมาก

## 2. ทำไมต้อง PySide6

- ต้องการ desktop GUI หนึ่งหน้าต่าง + form ให้เครื่องมือที่ user ใช้จริง
- PySide6 เป็น Qt binding ทางการ ให้ widget ครบ (`QTreeWidget`, `QFormLayout`, `QComboBox`, `QDoubleSpinBox` ฯลฯ) และติดตั้ง/รันบน Windows ได้ตรง ๆ ด้วย Python ที่ user มีอยู่แล้ว (3.11)
- ต่างจาก Tauri (ต้อง node + Rust toolchain) และ Electron (ต้อง node) — ที่นี่ไม่ต้องมี node เลย ซึ่งตรงกับ "ห้าม npm" ของโปรเจกต์

## 3. สถาปัตยกรรมรันไทม์

แยกเป็นสองชั้นชัดเจน:
- **Data layer** (`config_model.py`) — pure dict/list, รับผิดชอบโหลด/บันทึก/validate เท่านั้น ไม่รู้จัก widget
- **UI layer** (`main_window.py`, `provider_panel.py`, `mcp_panel.py`) — จัดการ widget, อ่าน/เขียนค่าผ่าน `ConfigModel`, เรียก `commit()` ก่อน `save()`

นี้สำคัญเพราะ schema validation และ save ต้องเป็นอิสระจาก GUI เพื่อทดสอบ headless ได้

## 4. โมดูล

| โมดูล | หน้าที่ |
|---|---|
| `config_model.py` | `load()`, `save()`, `schema_errors()`, `fetch_schema()`, `providers`, `mcp` |
| `main_window.py` | `MainWindow`: toolbar, mode switcher, `open/save/reload/validate` |
| `provider_panel.py` | tree provider/model + ฟอร์ม provider + ฟอร์ม model |
| `mcp_panel.py` | list mcp + ฟอร์ม local/remote |
| `test_smoke.py` | ยิง round-trip โดยไม่เปิดหน้าจอ |

## 5. Config: รากฐานข้อมูล

ทั้งแอปหมุนรอบ dict ตัวเดียว `config.data` ซึ่งเป็นสิ่งที่ `json.load` ตรงจาก `opencode.json` ได้ ไม่มี DB — save คือเขียน JSON กลับ `indent=2, ensure_ascii=False`

**ความระวัง:**
- `model` / `small_model` เป็น string `provider/model-id` (เช่น `inferx/deepseek-v4-flash-0731`)
- `skills` เป็น object (`paths`/`urls`) ไม่ใช่ array
- `agent` เป็น object keyed-by-name
- `plugin` เป็น array
- `mcp[name].command` เป็น array ไม่ใช่ string; `type` จำเป็น
- `permission` เป็น string หรือ object keyed-by-tool

## 6. API

ไม่มี HTTP endpoint ภายใน แต่มี interface กับ **external schema** คือ `https://opencode.ai/config.json` ที่ถูก `requests.get` ดึงมา validate ดู `docs/API.md`

## 7. กับดักบิว

- **PyInstaller** ต้อง bundle PySide6: ใช้ `--collect-all PySide6` หรือ `--collect-binaries PySide6` มิฉะนั้นแอปเปิดมาเ้ด่นรายงาน error หา plugin แพลตฟอร์ม
- **QDoubleSpinBox** ไม่เก็บข้อความ — ถ้า user ต้องการราคา "0.007" ต้องตั้ง `decimals=4` (ตั้งแล้ว)
- **env vs environment**: config ของ opencode ในป่าใช้ทั้ง `env` และ `environment` สำหรับ mcp; editor ต้อง preserve key เดิม (ดู `mcp_panel.py` `_env_key`)
- **offscreen test**: ตั้ง `QT_QPA_PLATFORM=offscreen` เพื่อรัน GUI ใน CI/headless

## 8. ความปลอดภัย

- apiKey ของ provider เก็บ plaintext ใน `opencode.json` อยู่แล้ว — **editor ต้องไม่เผลอแสดงเป็นข้อความโล่ง** → use `QLineEdit.Password` สำหรับช่อง apiKey
- ห้าม committ `opencode.json` จริงหรือ apiKey ลง git
- การ validate ไม่ควร ดาวน์โหลด schema เมื่อ offline — `fetch_schema()` คืน `{}` ให้ caller จัดการ

## 9. เทส

- `test_smoke.py` — ใช้ offscreen platform, load config จริง, สร้าง window, commit + save + reload แล้วเทียบ keys ว่าครบ
- จุดที่ยังไม่มี: unit test per-field ของ `config_model` (ราคา parse, schema error formatting)

## 10. Roadmap

ดู `docs/PLAN.md` — v1 ครอบ provider/model/ราคา/context/mcp; v2+ อาจเพิ่ม `agent` / `skill` / `permission` tabs และ live preview JSON
