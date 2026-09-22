# HT-CN Stable v1.0.0 Operator Runbook

HT-CN Stable 是本地优先的 A 股谐波研究与人工辅助决策产品。它不自动下单，也不会在证据不足时展示胜率、Alpha、盈利能力或统计显著性。

## 正常安装与启动

正式 release ZIP 已包含 built Web。解压后双击 `安装HT-CN.bat`，日常双击 `启动HT-CN.bat`。一个后台 supervisor 统一管理 API、built Web、M9.1 自动行情、M9.2 自动谐波运行时和 M9.4 后台证据服务。正常停止使用 `停止HT-CN.bat`。

正式安装包以 `HTCN_RELEASE_IDENTITY.json` 和 SHA-256 清单验证代码身份；开发 checkout 仍以 clean Git 为最高优先级。身份校验失败必须停止，不得绕过。

## 日常工作流

1. 启动 HT-CN。
2. 查看顶部产品运行层、自动行情、自动谐波、后台证据状态。
3. 选择本地已初始化标的。
4. 查看 K 线、谐波几何、比例、Raw PRZ/PEZ、目标与 lifecycle。
5. 使用“现在在哪 · 先看哪 · 到了再看哪”做人工决策支持。
6. 需要复盘时使用 operator queue/history/review。
7. 正常关闭时使用停止入口。

平移、缩放、crosshair 和 hover 只改变呈现，不会重新定义谐波身份。

## 证据不足状态

ISSUE-0066 允许在 Stable v1.0.0 期间保持 open。此时产品正常运行，M7 继续后台积累，M8 统计校准保持禁用，不展示胜率、Alpha、盈利能力或统计显著性。“证据不足”不是产品故障，也不需要每天人工运行 BAT、生成 ZIP 或让 AI 陪跑。

## 更新、备份与恢复

- `更新HT-CN.bat`：验证 pending release ZIP，生成 pre-update 备份，更新 immutable release 文件，重新验证并失败回滚。
- `备份HT-CN.bat`：生成带 SHA-256 清单的 mutable research/product state 备份。
- `恢复HT-CN.bat`：先验证备份，再 staging 恢复；未验证 ZIP、路径穿越或哈希不匹配一律拒绝。

完整恢复边界见 `docs/RECOVERY_CONTRACT.md`。

## supervisor 状态

- healthy：全部子服务正常；
- degraded：非关键服务自动退避恢复；
- blocked：关键服务 crash-loop 或前置身份/迁移失败；
- stopped：正常停止。

反复失败时查看 `artifacts/logs/m9-product-supervisor/`。禁止删除日志或直接改状态 JSON 伪造 healthy。

## 能力边界

Stable v1.0.0 支持既有冻结的 AB=CD、Gartley/Bat/Butterfly/Crab/Deep Crab、Shark 0XABC、Source Clock lifecycle 和人工辅助决策工作台。5-0 继续 quarantined；Alternate Bat 继续 fail-closed；HSI unsupported。

正常日常流程不包括：手工 M7 BAT、每日 evidence ZIP、AI 陪跑、Vite dev server、多终端服务管理或通过改 Git 让证据流程通过。
