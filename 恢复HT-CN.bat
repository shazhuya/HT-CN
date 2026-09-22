@echo off
setlocal
cd /d "%~dp0"

echo [HT-CN] 将恢复 backups 目录中最新的已验证备份。
choice /C YN /N /M "继续恢复？[Y/N] "
if errorlevel 2 exit /b 0

call "停止HT-CN.bat"
if errorlevel 1 exit /b 1

.venv\Scripts\python.exe scripts\m9_product_restore.py
if errorlevel 1 (
  echo [HT-CN] 恢复失败；原数据未通过未验证包写入。
  pause
  exit /b 1
)

call "启动HT-CN.bat"
exit /b 0
