# HT-CN Local

HT-CN 是一个面向中国 A 股实战的本地优先谐波交易研究与辅助决策系统。

## 核心原则

- 本地优先：核心功能在 Windows 本地运行。
- 零订阅：核心功能不依赖付费 SaaS、付费 API、云数据库或 TradingView 会员。
- 方法论可追溯：以 Scott M. Carney《Harmonic Trading》Volume One / Two / Three 为理论基准，并将 A 股增强规则与原始规则分层管理。
- Source Fidelity：原书 Identity / PRZ / Terminal Price Bar / Type-I / Type-II 与 HT-CN 工程近似必须显式分层；有源规则冲突时 fail closed。
- Agent First：具备自动测试、回归测试、浏览器自动化、截图与调试数据输出能力。
- 数据源可替换：市场数据通过 Adapter 层接入。
- 交易辅助：系统只辅助研究和决策，不执行交易。

## 技术栈

- Core / Data / API: Python 3.13 + FastAPI
- Web: React + TypeScript + Vite
- Chart: TradingView Lightweight Charts
- Storage: DuckDB + Parquet
- Testing: pytest + Playwright
- Version control: Git + GitHub

## 里程碑

- M0 ✅ 工程骨架、本地启动、自动测试基础设施
- M1 ✅ A 股数据层、证券主表、日线、QFQ/HFQ、智能增量与健康检查
- M2 ✅ Pivot / Fibonacci / 标准 Pattern / AB=CD / Shark / Reaction vs. Reversal / Terminal Price Bar 研究基础
- M2.26 ✅ Source Fidelity Repair 主体：双时钟、PRZ 分层、严格 Type-II、5-0 quarantine、Shark target contract
- M2.27 ✅ 标准 XABCD Source Raw PRZ Golden Profiles / v3
- M2.28 ✅ standalone AB=CD Source Raw PRZ / v4
- M2.29 ✅ 5-0 V2 structural Source Raw PRZ + V3 execution refinement 分层 / v5；production quarantine 保持
- M2.30 ✅ Shark Source Raw PRZ + source-aligned Terminal / management / v6；真实 A 股研究 CI 韧性修复
- M2.31 ▶ **当前 Gate：RSI BAMM Dedicated Source State Machine**
- M3 ⏸ Phase 1 工作台保留；正常 execution overlay 扩张等待 Source Fidelity Gate 关闭并迁移到 source-aligned live execution clock
- M4：Frontier / Activation / Lifecycle 形成中实时状态机产品化
- M5：Priority + A 股 execution / tradability 环境层
- M6：全 A 历史日线建库覆盖收口
- M7：全市场 Scanner
- M8：分钟数据智能缓存
- M9：Agent QA / Visual Regression 完整闭环

## 当前状态（2026-09-17）

项目已经完成标准 XABCD、standalone AB=CD、5-0 structural research contract 与 Shark Source Raw PRZ 的主要 source-fidelity 修复，并把 retrospective D geometry 与 source-aligned Terminal Price Bar execution clock 分离。

### M2.30 Shark freeze

Shark Source Raw PRZ = `0B 0.886–1.13 completion corridor` 与 `AB 1.618–2.24 Extreme Harmonic Impulse corridor` 的几何 overlap。两条 source corridors 不重叠时 fail closed；legacy Ideal Core 不得替代 Source Raw PRZ。

Shark reaction management 从 observed Terminal Price Bar extreme 开始：initial target 为 50% BC 与 Reciprocal AB=CD 中先被遇到的一档；61.8% BC 是更宽的 prospective 5-0 management level。上述 reaction measurements 不属于 Shark identity / Source Raw PRZ。

5-0 的 V2 structural Raw PRZ 已在 M2.29 冻结为 `50% BC + Reciprocal AB=CD`；V3 61.8 继续只属于 execution refinement。由于 V3 标签冲突尚未完全 source-certify，5-0 仍默认从 Engine / Scanner / Workbench 隔离。

### v6 真实 A 股验收

45-symbol frozen QFQ snapshot dataset，cutoff `2026-09-15`：

- cache 45 hit / 0 miss；
- calibration 约 85 秒；
- forming signals 8244；
- mature Source-Raw-PRZ Terminal events 1499；
- Train / Validation / sealed Holdout = 871 / 265 / 328；
- Shark terminal events = 76 / 26 / 40；
- historical v1/v3/v4/v5、Holdout、external replication 保持冻结；
- v6 confirmatory inference = false。

GitHub Actions run #603 / `35186542998` 全链 success。

### 下一 Gate

当前唯一主任务是 M2.31：把 RSI BAMM 从普通 Wilder RSI evidence 中彻底拆出来，按原书建立独立、多步骤、no-lookahead 状态机与 Book Golden regression。完成前，任何普通 RSI oversold/overbought 反转都不得叫 BAMM。

M2 本地统一验收入口仍为 `运行M2综合验收.bat`。前瞻登记是独立持续研究流程：`运行M2前瞻Type-I登记.bat`；普通 acceptance 不得修改冻结前瞻研究记录。

## 跨对话无损续接

HT-CN 不把长聊天记录当作项目事实数据库。任何新 ChatGPT / Codex / Agent 会话开始“继续 HT-CN”前，先读取 `AGENTS.md`、`PROJECT_CONTEXT.md`、`DECISIONS.md`，再检查 `PROJECT_CONTEXT.md` 的 `context_checkpoint..HEAD`、相关 `specs/` 和最新 CI。

- `AGENTS.md`：Bootstrap、会话收尾与权威顺序；
- `PROJECT_CONTEXT.md`：当前阶段、Gate、冻结约束、未解决问题、下一步；
- `DECISIONS.md`：设计原因与不可回归决策；
- `SESSION_LOG.md`：开发 Session 交接摘要；
- `生成HT-CN续接包.bat`：生成 `logs/context/HTCN_CONTEXT_PACK.md`；
- `检查HT-CN续接状态.bat`：检查 checkpoint 与 HEAD 关系。

仓库当前 HEAD、源码、测试与 CI 始终高于聊天记忆；旧聊天若与仓库冲突，以仓库为准。
