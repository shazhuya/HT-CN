@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] Dependencies are not installed. Run install script first.
  pause
  exit /b 1
)

if not exist "apps\web\node_modules" (
  echo [HT-CN] Web dependencies are missing. Run install script first.
  pause
  exit /b 1
)

echo [HT-CN] Starting API: http://127.0.0.1:8765
start "HT-CN API" cmd /k "cd /d %~dp0 && .venv\Scripts\python.exe -m uvicorn services.api.main:app --host 127.0.0.1 --port 8765 --reload"

echo [HT-CN] Starting Web: http://127.0.0.1:5173
start "HT-CN Web" cmd /k "cd /d %~dp0apps\web && npm run dev -- --host 127.0.0.1"

timeout /t 3 /nobreak >nul
start "" "http://127.0.0.1:5173"
exit /b 0
