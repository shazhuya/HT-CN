@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] 尚未安装依赖，请先双击“安装HT-CN.bat”。
  pause
  exit /b 1
)

if not exist "apps\web\node_modules" (
  echo [HT-CN] Web 依赖不存在，请先双击“安装HT-CN.bat”。
  pause
  exit /b 1
)

echo [HT-CN] 启动 API: http://127.0.0.1:8765
start "HT-CN API" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m uvicorn services.api.main:app --host 127.0.0.1 --port 8765 --reload"

echo [HT-CN] 启动 Web: http://127.0.0.1:5173
start "HT-CN Web" cmd /k "cd /d %~dp0apps\web && npm run dev -- --host 127.0.0.1"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
exit /b 0
