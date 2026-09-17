@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"

echo [HT-CN M3] 正在检查真实 M1 security_master / parquet / 当日交易事件元数据...
python scripts\m3_metadata_tradability_smoke.py
set ERR=%ERRORLEVEL%

if not "%ERR%"=="0" (
  echo [HT-CN M3] 检查未通过。请查看 artifacts\reports\m3-metadata-tradability-smoke.json
  exit /b %ERR%
)

echo [HT-CN M3] 检查完成。报告：artifacts\reports\m3-metadata-tradability-smoke.json
exit /b 0
