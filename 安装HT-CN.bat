@echo off
setlocal EnableDelayedExpansion
cd /d "%~dp0"

echo [HT-CN] 正在检查 Python 3.13...
python --version || goto :error

set "HTCN_GIT_HEAD="
if exist ".git" (
  for /f %%H in ('git rev-parse HEAD 2^>nul') do set "HTCN_GIT_HEAD=%%H"
)

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] 正在创建产品运行环境...
  python -m venv .venv || goto :error
)

echo [HT-CN] 正在安装运行依赖...
.venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
.venv\Scripts\python.exe -m pip install -e . || goto :error

set "HTCN_NEED_WEB_BUILD=0"
if not exist "apps\web\dist\index.html" set "HTCN_NEED_WEB_BUILD=1"

if defined HTCN_GIT_HEAD (
  set "HTCN_BUILT_HEAD="
  if exist "apps\web\dist\.htcn-build-head" (
    set /p HTCN_BUILT_HEAD=<"apps\web\dist\.htcn-build-head"
  )
  if /I not "!HTCN_BUILT_HEAD!"=="!HTCN_GIT_HEAD!" set "HTCN_NEED_WEB_BUILD=1"
)

if "!HTCN_NEED_WEB_BUILD!"=="1" (
  echo [HT-CN] 当前源码 Web 与 Git HEAD 不一致，正在重新构建...
  node --version || goto :web_error
  pushd apps\web
  call npm ci || goto :error_pop
  call npm run build || goto :error_pop
  popd
  if defined HTCN_GIT_HEAD (
    >"apps\web\dist\.htcn-build-head" echo !HTCN_GIT_HEAD!
  )
)

echo [HT-CN] 正在验证产品身份与运行环境...
.venv\Scripts\python.exe scripts\m9_product_supervisor.py --check || goto :error

echo.
echo [HT-CN] 安装完成。以后直接双击“启动HT-CN.bat”。
pause
exit /b 0

:error_pop
popd
:error
echo.
echo [HT-CN] 安装失败。请保留本窗口错误信息，使用恢复入口或报告故障。
pause
exit /b 1

:web_error
echo.
echo [HT-CN] 源码安装缺少已构建 Web 且未检测到 Node.js。
echo [HT-CN] 正式 release ZIP 不需要 Node.js；请改用正式发布包。
pause
exit /b 1
