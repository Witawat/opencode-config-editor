@echo off
rem ============================================================
rem  build.bat — วางงาน Single-file EXE (PyInstaller)
rem
rem  วิธีใช้:  double-click ไฟล์นี้ หรือสั่งจาก cmd:
rem      build.bat
rem      build.bat --clean      (ลบ build/dist ก่อนบิ้ว)
rem
rem  ต้องมี venv (.venv) และติดตั้ง pyinstaller ก่อน (หนึ่งครั้ง):
rem      .venv\Scripts\pip install pyinstaller
rem ============================================================
setlocal

cd /d "%~dp0"

set PY=.venv\Scripts\python.exe
set PYINST=.venv\Scripts\pyinstaller.exe

if not exist "%PY%" (
    echo [ERROR] venv ยังไม่ถูกสร้าง
    echo         สร้างดวย:  .venv\Scripts\pip.cmd ตามคำสั่งใน docs\BUILD.md
    pause
    exit /b 1
)

if not exist "%PYINST%" (
    echo [INFO] pyinstaller ยังไมติดตั้ง... กำลังติดตั้ง
    "%PY%" -m pip install pyinstaller
    if errorlevel 1 (
        echo [ERROR] ติดตั้ง pyinstaller ไมสำเร็จ
        pause
        exit /b 1
    )
)

set CLEAN_FLAG=
if /i "%~1"=="--clean" set CLEAN_FLAG=--clean

echo [1/2] ตรวจไฟลล์...
if not exist "assets\opencode.ico" (
    echo [WARN] ไมพบ assets\opencode.ico — ไอคอนจะไมติดบน exe
)

echo [2/2] เริ่มบิ้ว (PyInstaller onefile + windowed + icon)...
"%PYINST%" --noconfirm %CLEAN_FLAG% opencode_editor.spec
if errorlevel 1 (
    echo [ERROR] บิ้วไมสำเร็จ — ดุ log ดานบน
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  เสร็จแลว: dist\opencode-config-editor.exe
echo  (double-click เปดไดทันที ไมมี console)
echo ============================================================
pause
