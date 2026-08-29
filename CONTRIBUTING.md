# CONTRIBUTING.md — แนวทางมีส่วนร่วม

## ก่อนเริ่ม

- อ่าน `AGENTS.md` — ส่วนใหญ่กฎของโค้ดอยู่ตรงนั้น (สแตกที่ล็อก + ห้ามทำ)
- อ่าน `README.md` เพื่อภาพรวม

## ขั้นตอนทำงาน

1. Fork / สร้าง branch
2. ทำการเปลี่ยนแปลง — ปฏิบัติตาม "ห้ามทำ" ใน `AGENTS.md`
3. เทส: รันชุดเทสให้ผ่าน — `test_roundtrip.py` (unit), `test_functional.py <copy-config>` (e2e), `test_smoke.py`
4. Commit ตาม [Conventional Commits](https://www.conventionalcommits.org/) เช่น `feat`, `fix`, `docs`, `refactor`
5. เปิด PR — อธิบายผลที่เปลี่ยน (ก่อน/หลัง) ให้ชัด

## สแตกที่อนุญาต

- Python 3.11+, PySide6, jsonschema, requests
- **ห้าม** เพิ่ม Node/npm/JS และ WebUI ใด ๆ

## การเขียนโค้ด

- **UI แยกจาก data**: ฟอร์มแก้ค่าต้องผ่าน `ConfigModel` เท่านั้น ไม่เข้าถึงไฟล์ตรง
- **Merge ไม่ rebuild**: ทุก panel commit ต้อง merge เฉพาะ field ที่รู้จัก — ห้ามสร้าง dict ใหม่ทิ้ง key ที่ UI ไม่รู้จัก (`interleaved`, `toolbar`, ฯลฯ)
- **Preserve key**: ตอน save อย่าลืม `$schema`, `env`/`environment`
- **Touch-sensitive**: ค่า 0 / uncheck ที่ไม่ได้แก้ อย่าเขียนทับ (ดู `_orig_cost`, `_cost_edited`, `_comp_touched`)
- **Type hints**: ใช้ `from __future__ import annotations`
- **ความปลอดภัย**: อย่า commit `opencode.json` จริง หรือ apiKey — preview/copy ต้องผ่าน `mask_secrets()`
- **ฟีเจอร์ใหม่มีปุ่ม ต้องมี test สอง**

## เทสและ lint

- Scaffold มี `test_smoke.py`; ถ้ามี `ruff`/`pytest` เพิ่มเติม แนะนำใช้งาน
- ยืนยันว่า `%QT_QPA_PLATFORM%` ตั้งเป็น `offscreen` เมื่อเทส headless

## รายงานปัญหา

อธิบาย: สิ่งที่ทำ, ผลที่คาดหวัง, ผลที่เจอ, สภาพแวดล้อม (Python, OS, PySide6 version) และ steps ที่เป็นซ้ำได้
