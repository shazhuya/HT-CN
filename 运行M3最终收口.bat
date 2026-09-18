@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [HT-CN M3 CLOSEOUT] 未找到 .venv，请先安装环境。
  pause
  exit /b 1
)

if not exist "data\market\catalog.duckdb" (
  echo [HT-CN M3 CLOSEOUT] 未找到真实 M1 catalog。
  pause
  exit /b 1
)

echo ============================================================
echo HT-CN M3 最终收口
echo 1/4 M1 智能日更（base + daily_delta）
echo 2/4 确定性工作台验收
echo 3/4 四层上下文真实同步
echo 4/4 当前 HEAD 合并就绪判定
echo ============================================================
echo.

.venv\Scripts\python.exe scripts\m1_daily_update.py
set M1_EXIT=%ERRORLEVEL%

echo.
echo [HT-CN M3 CLOSEOUT] 运行严格工作台验收...
.venv\Scripts\python.exe scripts\qa_local.py
set QA_EXIT=%ERRORLEVEL%

echo.
echo [HT-CN M3 CLOSEOUT] 运行四层上下文同步...
.venv\Scripts\python.exe scripts\m3_sync_all_contexts.py
set CONTEXT_EXIT=%ERRORLEVEL%

echo.
echo [HT-CN M3 CLOSEOUT] 生成合并就绪报告...
.venv\Scripts\python.exe scripts\m3_pr_readiness.py
set READY_EXIT=%ERRORLEVEL%

echo.
echo ============================================================
echo M1 exit=%M1_EXIT% / QA exit=%QA_EXIT% / Context exit=%CONTEXT_EXIT% / Ready exit=%READY_EXIT%
echo 工作台：artifacts\reports\m3-workbench-acceptance.json
echo 上下文：artifacts\reports\m3-context-sync-summary.json
echo 就绪报告：artifacts\reports\m3-pr-readiness.json
echo 中文报告：artifacts\reports\m3-pr-readiness.md
echo ============================================================
if %READY_EXIT% EQU 0 (
  echo [HT-CN M3 CLOSEOUT] READY：没有硬阻断；请查看 warning 和固定边界。
) else (
  echo [HT-CN M3 CLOSEOUT] NOT READY：请先处理 m3-pr-readiness.md 中的硬阻断。
)
pause
exit /b %READY_EXIT%
