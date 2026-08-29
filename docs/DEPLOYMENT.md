# DEPLOYMENT.md — การ deploy (Windows)

## แนวคิด

โปรเจกต์นี้เป็น desktop GUI — "deploy" คือการทำให้ผู้ใช้เปิดได้ง่ายบนเครื่อง Windows ที่อาจไม่มี Python ติดตั้ง โดยไม่มี console ผุดขึ้น และไม่ได้พึ่ง npm/toolchain ภายนอก

## โหมด 1: ใช้ `.venv` โดยตรง (dev / ของตัวเอง)

```powershell
run.bat
```
เพียง double-click `run.bat` — มันเช็คว่า venv มีไหม ถ้าไม่มีแจ้งวิธีตั้งค่า

## โหมด 2: `.exe` จาก build

ดู `docs/BUILD.md` → ได้ `dist\opencode-config-editor.exe`

- ส่งไฟล์ `.exe` เดียวไปให้ผู้ใช้ได้เลย
- ตรวจแต่ละเครื่อง ที่จะรัน: ไม่ต้องมี Python — PyInstaller bundle ให้แล้ว
- **ผู้ใช้อาจมี Python/logic ต่างกัน**: ผู้อ่าน `~/.config/opencode/opencode.json` ตามสิทธิ์ ที่ user รัน

## โหมด 3: ทำเป็น shortcut / service (เพิ่มความสะดวก)

### 3a. Shortcut บน Desktop

สร้าง `.lnk` ชี้ไป `dist\opencode-config-editor.exe` หรือ `run.bat` — กดเปิดง่ายขึ้น

### 3b. ลงทะเบียนเป็น service ด้วย NSSM (ทางเลือก สำหรับใช้ต่อเนื่อง)

> มักไม่จำเป็นสำหรับ desktop GUI — service ต้องไม่ต้อง man-เกินไปถ้าใช้ `--windowed` อยู่แล้ว ใช้ NSSM เฉพาะถ้าต้องให้รันพร้อม machine และมี account sessile มากพอ

```powershell
nssm install OpenCodeConfigEditor "D:\MyCode\opencode-config-editor\dist\opencode-config-editor.exe"
nssm set OpenCodeConfigEditor AppDirectory "D:\MyCode\opencode-config-editor"
nssm start OpenCodeConfigEditor
```

> ⚠️ GUI app ลงเป็น service วินโดว์-level จะไม่เห็นหน้าต่างใน user session ปกติ เพราะ service รันที่ session 0 — ใช้ได้ดีกับ "เปิดแอปแบบ มี notification area/auto-start" แต่ถ้าใช้งานจริง ใช้ shortcut ที่ `shell:startup` จะสมเหตุสมผลกว่า

### 3c. Auto-start เมื่อ login

วาง shortcut ใน `shell:startup`:

```
Win+R → shell:startup → Enter → วาง .lnk ชี้ run.bat หรือ .exe
```

## config ไฟล์ที่แอปอ่าน

`ConfigModel.DEFAULT_CONFIG_PATH` = `%USERPROFILE%\.config\opencode\opencode.json`
- ถ้าไม่ตั้ง default → เปิด `python main.py "path\ที่กำหนด"`

## หมายเหตุ

- **ห้าม deploy ไปบนเครื่องที่ต้องใช้ schema validate online** — แอปยังต้องต่อเน็ตเมื่อกด "ตรวจ Schema"
- **apiKey**: ไม่ควร commit ไฟล์ config จริง — ใช้ `{env:VAR}` และให้ user ตั้ง env variables
