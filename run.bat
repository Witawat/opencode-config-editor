@echo off
setlocal
set "PY=.venv\Scripts\python.exe"
if not exist "%PY%" (
  echo [ERROR] venv not found. Run: python -m venv .venv ^&^& .venv\Scripts\pip install -r requirements.txt
  pause
  exit /b 1
)
"%PY%" main.py %*
