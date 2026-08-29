# BUILD.md — การบิลด์ (Python + PySide6)

## สิ่งที่บิลด์

GUI แบบ desktop — ต้องการผลลัพธ์เป็น `.exe` (.single executable) ที่เปิดบน Windows โดยไม่ต้องติดตั้ง Python

## ข้อกำหนด

- Python 3.11+ (64-bit แนะนำ)
- venv ที่ติดตั้ง `requirements.txt` แล้ว
- แนะนำ build บน `win-x64` (เครื่องเดียวกันกับที่รัน)

## ขั้นตอน

### 1. เตรียม venv

```powershell
cd D:\MyCode\opencode-config-editor
python -m venv .venv
.venv\Scripts\pip install -r requirements.txt
```

### 2. ติดตั้ง build tool

เลือก PyInstaller หรือ Nuitka อย่างใดอย่างหนึ่ง:

**PyInstaller (แนะนำ - ง่ายสุด)**

```powershell
.venv\Scripts\pip install pyinstaller
```

### 2.5. ใช้ `build.bat` (ทางลัด)

```powershell
build.bat            # บิ้วแบบปกติ (ถ้าขาด pyinstaller จะติดตั้งให้เอง)
build.bat --clean    # ลบ build/dist ก่อนบิ้ว
```

- เรียกใช้ด้วย double-click หรือ cmd ได้เลย
- อ่าน `opencode_editor.spec` (onefile + windowed + icon opencode.ico)
- ผลลัพธ์: `dist\opencode-config-editor.exe` (~48 MB)

**Nuitka (ทางเลือก - ไฟล์เล็ก เปิดไว แต่ build ช้า)**

```powershell
.venv\Scripts\pip install nuitka ordered-set
```

### 3. บิลด์

#### PyInstaller

มี spec ที่พร้อมแล้ว (`opencode_editor.spec`) — ใช้ไอคอน opencode จาก `assets/opencode.ico` และ `--windowed`:

```powershell
.venv\Scripts\pyinstaller --noconfirm --clean opencode_editor.spec
```

หรือสั่งตรงแบบเดิม:

```powershell
.venv\Scripts\pyinstaller --noconfirm --onefile --windowed `
  --name "opencode-config-editor" `
  --icon "assets\opencode.ico" `
  --collect-all PySide6 `
  main.py
```

- `--windowed`: สำคัญ — ไม่ให้หน้าต่าง console ผุดขึ้น
- `--collect-all PySide6`: สำคัญ — bundle plugin platform (qwindows) ครบ; ทิ้งแล้วแอปพังตอนเปิด
- `--icon`: ไอคอน opencode (สกัดจาก repo ทางการ — `assets/opencode.ico`)

ผลลัพธ์: `dist\opencode-config-editor.exe` (~48 MB)

ตรวจ: `dist\opencode-config-editor.exe` เปิดแล้วขึ้น window

#### Nuitka

```powershell
.venv\Scripts\python -m nuitka --onefile --enable-plugin=pyqt6 --windows-console-mode=disable --output-dir=dist main.py
```

ผลลัพธ์: `dist\main.exe` (ต่อยอดตั้งชื่อและ icon ได้ด้วย `--output-filename`)

## ทางเลือก: ไม่บิลด์ (ใช้ตรง ๆ)

```powershell
run.bat
```
หรือ
```powershell
.venv\Scripts\python.exe main.py
```

## หมายเหตุ

- **PyInstaller + PySide6**: ไฟล์ราว 40–80 MB ถือว่าปกติ (Qt big)
- อยากไม่โดน antivirus flag: Nuitka มักได้ไฟล์ที่ใจร้ายน้อยกว่า แต่ต้องยอม build ช้าและ config เพิ่ม
- **เช็ค dist กับไฟล์ config จริง**: อย่าลืมว่า `.exe` ยังอ่านconfig ที่ `~/.config/opencode/opencode.json` (ถ้าเปิดแบบ double click)

## ข้อผิดพลาดที่เจอบ่อย

| อาการ | สาเหตุ | วิธีแก้ |
|---|---|---|
| เปิด `.exe` แล้วพังทันที/ได้ข้อความ Qt platform plugin | ไม่ได้ `--collect-all PySide6` | เพิ่ม flag |
| ปิดไม่ได้/หน้าต่าง console โผล่ | ลืม `--windowed` | เพิ่ม flag |
| ฟอนต์/กิริยา UI เพี้ยน | ใช้ได้ แต่ต้องเรียกผ่าน venv | ไม่ใช่ bug — reinstall PySide6 |
