@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\pythonw.exe" (
  call "安装HT-CN.bat"
  if errorlevel 1 exit /b 1
)

if not exist "apps\web\dist\index.html" (
  call "安装HT-CN.bat"
  if errorlevel 1 exit /b 1
)

.venv\Scripts\python.exe scripts\m9_product_supervisor.py --check >nul 2>&1
if errorlevel 1 (
  echo [HT-CN] 产品前置检查失败，请运行“恢复HT-CN.bat”或查看 artifacts\logs。
  pause
  exit /b 1
)

start "" ".venv\Scripts\pythonw.exe" "scripts\m9_product_supervisor.py"
timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
exit /b 0
