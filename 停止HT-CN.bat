@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" exit /b 0
.venv\Scripts\python.exe scripts\m9_product_control.py stop
if errorlevel 1 (
  echo [HT-CN] 未能在限定时间内确认 supervisor 停止，请查看产品状态。
  pause
  exit /b 1
)
exit /b 0
