@echo off
setlocal
cd /d "%~dp0"

echo [HT-CN] Checking Python...
python --version || goto :error

echo [HT-CN] Checking Node.js...
node --version || goto :error

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] Creating Python virtual environment...
  python -m venv .venv || goto :error
)

echo [HT-CN] Installing Python dependencies...
.venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
.venv\Scripts\python.exe -m pip install -e ".[dev]" || goto :error

echo [HT-CN] Installing Web dependencies...
pushd apps\web
call npm install || goto :error_pop
call npx playwright install chromium || goto :error_pop
popd

echo.
echo [HT-CN] Installation completed.
pause
exit /b 0

:error_pop
popd
:error
echo.
echo [HT-CN] Installation failed. Send the last error lines to ChatGPT.
pause
exit /b 1
