# HT-CN Local

HT-CN 是一个面向中国 A 股实战的本地优先谐波交易研究与辅助决策系统。

## 核心原则

- 本地优先：核心功能在 Windows 本地运行。
- 零订阅：核心功能不依赖付费 SaaS、付费 API、云数据库或 TradingView 会员。
- 方法论可追溯：以 Scott M. Carney《Harmonic Trading》Volume One / Two / Three 为理论基准，并将 A 股增强规则与原始规则分层管理。
- Source Fidelity：原书 Identity / PRZ / Terminal Price Bar / Type-I / Type-II 与 HT-CN 工程近似必须显式分层；有源规则冲突时 fail closed，不能用评分、统计或 UI 偏好补救。
- Agent First：从第一版开始具备自动测试、回归测试、浏览器自动化、截图与调试数据输出能力。
- 数据源可替换：市场数据通过 Adapter 层接入，避免绑定单一免费数据源。
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
- M2 ✅ Pivot / Fibonacci / 标准 Pattern / 研究型 PRZ Core、AB=CD、Shark、Reaction vs. Reversal、Terminal Price Bar 研究管线、真实 A 股校准、冻结 Holdout / 外部复现、前瞻 Type-I append-only registry
- M2.26 ✅ **Source Fidelity Repair**：双时钟、Source PRZ / Ideal Core / PEZ 分层、严格 Type-II、5-0 源冲突隔离、Shark target contract、API v2 price-zone contract
- M2.27 ▶ **Source PRZ Golden Profiles（当前 Gate）**：标准 XABCD source-backed Raw PRZ、Book Case 证据、source / engineering provenance 分层、source-Raw-PRZ v3 research semantics
- M3 ⏸ 实战工作台产品化：Phase 1 的 K 线 / 形态 / 生命周期导航保留，但后续正常扩张需等待 Source Fidelity Gate 关闭，并把执行语义迁移到 source-aligned Terminal Price Bar 时钟
- M4：Frontier / Activation / Lifecycle 的形成中实时追踪与状态机产品化
- M5：Priority + A 股环境层（指数/板块相对强弱、流动性、涨跌停、T+1、ATR、开收盘微观结构等）；只影响执行/可交易性，不改写 Carney identity / source PRZ
- M6：全 A 历史日线建库覆盖收口
- M7：全市场 Scanner
- M8：分钟数据智能缓存
- M9：Agent QA / Visual Regression 完整闭环

## 当前状态（2026-09-17）

三卷书复核后，标准几何主干和既有研究资产继续保留，但项目已经明确把后验 D 点反应审计与 source-aligned Terminal Price Bar 执行时钟分离，并把 `component envelope`、`ideal convergence core`、`source Raw PRZ`、Terminal extreme 与 PEZ 分层管理。

`main` 已包含 M2.26 与 M2.27：

- 后验 D 时钟与 Terminal Price Bar 执行时钟已强制分离；
- 标准 XABCD 已建立 source-backed Raw PRZ profiles 与 Book Case evidence；
- source provenance 与 engineering provenance 已拆分；
- source PRZ 未解决时，相关执行语义继续 fail closed；
- Wilder RSI 辅助确认明确不是 RSI BAMM；
- 5-0 默认从 Engine / Scanner / Workbench 隔离，仅研究显式 opt-in；
- Shark 保持专属 first-target contract；
- source-Raw-PRZ v3 研究边界已经建立，历史 frozen results 不回写。

当前仍需继续关闭 Source Fidelity Gate，重点是剩余 Book Golden Set、Shark / 5-0 source conflict、完整 RSI BAMM 独立状态机，以及 M3 retrospective lifecycle overlay 向 source-aligned live execution-clock 语义迁移。

历史 45 股 Holdout、独立 60 股外部复现及既有前瞻登记继续作为已经消费/冻结的历史研究记录保存，不回头篡改。若 Source Fidelity Repair 改变未来候选资格或执行定义，应建立新的版本化前瞻协议，而不是改写旧结果。

M2 本地统一验收入口仍为 `运行M2综合验收.bat`。前瞻登记是独立持续研究流程：先完成 M1 日线更新，再运行 `运行M2前瞻Type-I登记.bat`；该流程不执行 interim significance test，也不输出动态“胜率”。

## 跨对话无损续接

HT-CN 不再把长聊天记录当作项目事实数据库。任何新 ChatGPT / Codex / Agent 会话开始“继续 HT-CN”前，先读取 `AGENTS.md`、`PROJECT_CONTEXT.md`、`DECISIONS.md`，再检查 `PROJECT_CONTEXT.md` 里的 `context_checkpoint..HEAD`、相关 `specs/` 和最新 CI。

- `AGENTS.md`：新会话 Bootstrap、会话收尾与权威顺序；
- `PROJECT_CONTEXT.md`：当前阶段、Gate、冻结约束、未解决问题、下一步；
- `DECISIONS.md`：为什么这样设计，防止旧方案失忆式回归；
- `SESSION_LOG.md`：每个开发 Session 的交接摘要；
- `生成HT-CN续接包.bat`：生成 `logs/context/HTCN_CONTEXT_PACK.md`，用于离线或手动交接；
- `检查HT-CN续接状态.bat`：检查续接元数据、checkpoint 与当前 HEAD 的关系。

仓库当前 HEAD、源码、测试与 CI 始终高于聊天记忆；旧聊天如果与新仓库冲突，以仓库为准。