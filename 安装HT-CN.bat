@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

echo [HT-CN] 正在检查 Python...
python --version || goto :error

echo [HT-CN] 正在检查 Node.js...
node --version || goto :error

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN] 创建 Python 虚拟环境...
  python -m venv .venv || goto :error
)

echo [HT-CN] 安装 Python 依赖...
.venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
.venv\Scripts\python.exe -m pip install -e ".[dev]" || goto :error

echo [HT-CN] 安装 Web 依赖...
pushd apps\web
call npm install || goto :error_pop
call npx playwright install chromium || goto :error_pop
popd

echo.
echo [HT-CN] 安装完成。
echo 以后双击“启动HT-CN.bat”即可运行。
pause
exit /b 0

:error_pop
popd
:error
echo.
echo [HT-CN] 安装失败。请把本窗口的错误截图发给 ChatGPT。
pause
exit /b 1
