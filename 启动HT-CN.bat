@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

set "HTCN_NEED_INSTALL=0"
if not exist ".venv\Scripts\pythonw.exe" set "HTCN_NEED_INSTALL=1"
if not exist "apps\web\dist\index.html" set "HTCN_NEED_INSTALL=1"

if exist ".git" (
  set "HTCN_GIT_HEAD="
  for /f %%H in ('git rev-parse HEAD 2^>nul') do set "HTCN_GIT_HEAD=%%H"
  set "HTCN_BUILT_HEAD="
  if exist "apps\web\dist\.htcn-build-head" (
    set /p HTCN_BUILT_HEAD=<"apps\web\dist\.htcn-build-head"
  )
  if defined HTCN_GIT_HEAD (
    if /I not "!HTCN_BUILT_HEAD!"=="!HTCN_GIT_HEAD!" set "HTCN_NEED_INSTALL=1"
  )
)

if "!HTCN_NEED_INSTALL!"=="1" (
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
