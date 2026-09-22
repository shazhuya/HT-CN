@echo off
setlocal
cd /d "%~dp0"

call "停止HT-CN.bat"
if errorlevel 1 exit /b 1

.venv\Scripts\python.exe scripts\m9_product_backup.py --label manual
if errorlevel 1 (
  echo [HT-CN] 备份失败。
  pause
  exit /b 1
)

echo [HT-CN] 备份完成，正在重新启动产品...
call "启动HT-CN.bat"
exit /b 0
