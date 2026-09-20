@echo off
chcp 65001 >nul
cd /d "%~dp0"
call "运行M4真实A股生命周期快照.bat"
exit /b %ERRORLEVEL%
