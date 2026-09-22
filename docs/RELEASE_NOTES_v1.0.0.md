# HT-CN Stable v1.0.0 Release Notes

Stable v1.0.0 是产品运行稳定版，不是统计收益成熟度声明。

## Included

- 自动 A 股行情调度、QFQ、retry/failover/health；
- 自动谐波运行时，保持 Source/lifecycle 语义；
- 中文端到端工作台：K 线、谐波、比例、PRZ、目标、lifecycle、共享 crosshair；
- 后台 M7 前瞻证据和明确的 insufficient-evidence 状态；
- 单 supervisor 管理 API、built Web、M9.1/M9.2/M9.4；
- 无 Git verified release identity，M4 37/37 与 Outcome 4/4 attestation；
- 一键 install/start/stop/update/backup/restore；
- 确定性 release package、backup verification、schema migration、update rollback。

## Intentionally unavailable

- 自动交易；
- ISSUE-0066 open 时的胜率、Alpha、盈利能力、统计显著性；
- 未通过既有授权 gate 的 M8 证据校准；
- 5-0 production；
- Alternate Bat production；
- HSI。

M7 在 v1.0.0 发布后继续后台积累；未来证据不会反向改写冻结 Source identity 或 M4 方法论。
