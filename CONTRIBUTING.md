# CONTRIBUTING.md — แนวทางมีส่วนร่วม

## ก่อนเริ่ม

- อ่าน `AGENTS.md` — ส่วนใหญ่กฎของโค้ดอยู่ตรงนั้น (สแตกที่ล็อก + ห้ามทำ)
- อ่าน `README.md` เพื่อภาพรวม

## ขั้นตอนทำงาน

1. Fork / สร้าง branch
2. ทำการเปลี่ยนแปลง — ปฏิบัติตาม "ห้ามทำ" ใน `AGENTS.md`
3. เทส: รัน `test_smoke.py` ให้ผ่าน (หรือเพิ่ม/แก้ unit test ตาม `PLAN.md` Phase 4)
4. Commit ตาม [Conventional Commits](https://www.conventionalcommits.org/) เช่น `feat`, `fix`, `docs`, `refactor`
5. เปิด PR — อธิบายผลที่เปลี่ยน (ก่อน/หลัง) ให้ชัด

## สแตกที่อนุญาต

- Python 3.11+, PySide6, jsonschema, requests
- **ห้าม** เพิ่ม Node/npm/JS และ WebUI ใด ๆ

## การเขียนโค้ด

- **UI แยกจาก data**: ฟอร์มแก้ค่าต้องผ่าน `ConfigModel` เท่านั้น ไม่เข้าถึงไฟล์ตรง
- **Preserve key**: ตอน save อย่าลืม `$schema`, `env`/`environment`
- **Type hints**: ใช้ `from __future__ import annotations`
- **ความปลอดภัย**: อย่า commit `opencode.json` จริง หรือ apiKey

## เทสและ lint

- Scaffold มี `test_smoke.py`; ถ้ามี `ruff`/`pytest` เพิ่มเติม แนะนำใช้งาน
- ยืนยันว่า `%QT_QPA_PLATFORM%` ตั้งเป็น `offscreen` เมื่อเทส headless

## รายงานปัญหา

อธิบาย: สิ่งที่ทำ, ผลที่คาดหวัง, ผลที่เจอ, สภาพแวดล้อม (Python, OS, PySide6 version) และ steps ที่เป็นซ้ำได้
