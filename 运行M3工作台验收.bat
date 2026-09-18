@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M3 ACCEPT] 未找到 .venv，请先运行安装脚本。
  pause
  exit /b 1
)

if not exist "apps\web\node_modules" (
  echo [HT-CN M3 ACCEPT] 未找到 Web 依赖，请先运行安装脚本。
  pause
  exit /b 1
)

if not exist "data\market\catalog.duckdb" (
  echo [HT-CN M3 ACCEPT] 未找到真实 M1 catalog：data\market\catalog.duckdb
  echo [HT-CN M3 ACCEPT] M3 正式验收要求真实本地数据库，不再只靠 fixture。
  pause
  exit /b 1
)

echo [HT-CN M3 ACCEPT] ============================================================
echo [HT-CN M3 ACCEPT] M3 工作台综合自动验收
echo [HT-CN M3 ACCEPT] 1. 全量 Python 回归
echo [HT-CN M3 ACCEPT] 2. TypeScript + Web build
echo [HT-CN M3 ACCEPT] 3. 真实 M1 metadata / tradability 只读 smoke
echo [HT-CN M3 ACCEPT] 4. 真实 M1 lifecycle / narrative / context 产品契约 smoke
echo [HT-CN M3 ACCEPT] 5. 本地 API + Workbench
echo [HT-CN M3 ACCEPT] 6. 全量 Playwright：Source overlay / Execution / Market / Industry
echo [HT-CN M3 ACCEPT]    / Concept / Context Integrity / Decision Narrative / Live
echo [HT-CN M3 ACCEPT]
echo [HT-CN M3 ACCEPT] 注意：本验收不联网刷新行业/概念，避免上游接口波动制造假失败。
echo [HT-CN M3 ACCEPT] 需要刷新四层数据时单独运行：运行M3上下文数据同步.bat
echo [HT-CN M3 ACCEPT] 不需要人工截图确认。
echo [HT-CN M3 ACCEPT] ============================================================
echo.

.venv\Scripts\python.exe scripts\qa_local.py
if errorlevel 1 goto :fail

echo.
echo [HT-CN M3 ACCEPT] ============================================================
echo [HT-CN M3 ACCEPT] M3 WORKBENCH ACCEPTANCE PASSED.
echo [HT-CN M3 ACCEPT] 元数据报告：artifacts\reports\m3-metadata-tradability-smoke.json
echo [HT-CN M3 ACCEPT] 产品契约：artifacts\reports\m3-product-contract-smoke.json
echo [HT-CN M3 ACCEPT] Playwright：artifacts\reports\playwright\index.html
echo [HT-CN M3 ACCEPT] 截图证据：artifacts\screenshots\
echo [HT-CN M3 ACCEPT] 无需把常规截图发给我；只有失败时保留最后错误块。
echo [HT-CN M3 ACCEPT] ============================================================
pause
exit /b 0

:fail
echo.
echo [HT-CN M3 ACCEPT] ============================================================
echo [HT-CN M3 ACCEPT] FAILED.
echo [HT-CN M3 ACCEPT] 请保留窗口最后的错误块。
echo [HT-CN M3 ACCEPT] 同时检查：
echo [HT-CN M3 ACCEPT] artifacts\reports\m3-metadata-tradability-smoke.json
echo [HT-CN M3 ACCEPT] artifacts\reports\m3-product-contract-smoke.json
echo [HT-CN M3 ACCEPT] artifacts\reports\playwright\
echo [HT-CN M3 ACCEPT] ============================================================
pause
exit /b 1
