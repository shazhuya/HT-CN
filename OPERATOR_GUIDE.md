# HT-CN Stable Product 操作指南

本指南适用于 M9.6 Stable Product。HT-CN 是中国 A 股谐波研究与人工辅助决策工具，**不执行证券交易**，也不会因为统计证据不足而伪造胜率、Alpha 或盈利能力结论。

## 日常使用

正常使用**无需命令行**、无需 Node/Vite、无需每日上传 ZIP，也不需要 AI 陪跑。

1. 首次安装或环境修复：双击 `安装HT-CN.bat`。
2. 日常启动：双击 `启动HT-CN.bat`。单一 supervisor 会管理 API、built Web、自动行情、自动谐波运行时和后台 evidence 服务。
3. 日常停止：双击 `停止HT-CN.bat`。
4. 备份、恢复、更新分别使用 `备份HT-CN.bat`、`恢复HT-CN.bat`、`更新HT-CN.bat`。

打开产品后先看运行状态，再进入标的研究工作台。市场数据与谐波 runtime 都应显示最新水位；后台证据卡片会把“运行故障”和“统计证据不足”分开显示。

## 统计能力边界

`ISSUE-0066` 仍可保持 open。它只限制胜率、Alpha、盈利能力、统计显著性和 evidence-based calibration 声明，不影响正常行情更新、谐波分析、工作台、后台 evidence、备份恢复或 Stable Product 使用。

当证据不足时，界面必须明确显示“证据不足 / M8 未启用”，而不是输出百分比或伪统计结论。

## 常见状态

- **运行正常**：核心服务已启动，built Web 正常，不需要 Vite。
- **降级**：非关键子服务正在重试；按产品内中文诊断处理。
- **阻塞**：关键服务、数据完整性或 release identity 验证失败；不要绕过验证，应按 Recovery Contract 恢复。
- **证据积累中**：产品本身可以正常使用，只是统计能力尚未解锁。

## 日常不应该做的事

不要为了正常使用每天手工运行 M7 BAT、上传 evidence ZIP、启动多个开发终端、运行 Vite dev server、清理或重写权威 evidence、修改冻结的 M4 methodology / Outcome Engine，或把产品当作自动下单系统。

需要恢复、升级或故障处理时，按 `RECOVERY_CONTRACT.md` 执行。
