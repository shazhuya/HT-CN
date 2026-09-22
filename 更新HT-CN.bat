@echo off
setlocal
cd /d "%~dp0"

echo [HT-CN] 将安装 updates 目录中最新的已验证 release ZIP。
choice /C YN /N /M "继续更新？[Y/N] "
if errorlevel 2 exit /b 0

call "停止HT-CN.bat"
if errorlevel 1 exit /b 1

.venv\Scripts\python.exe scripts\m9_apply_pending_update.py
if errorlevel 1 (
  echo [HT-CN] 更新失败；已保留 pre-update 备份，产品代码将保持或回滚到旧版本。
  pause
  exit /b 1
)

call "启动HT-CN.bat"
exit /b 0
