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
- M2.26 ▶ **Source Fidelity Repair（当前 Gate）**：双时钟、Source PRZ / Ideal Core / PEZ 分层、严格 Type-II、5-0 源冲突隔离、Book Golden Set。正常 M3 功能扩张在此 Gate 关闭前暂停。
- M3 ⏸ 实战工作台产品化：已完成的 K 线 / 形态 / 生命周期导航保留，但 T1/T2 等执行语义必须先迁移到 source-aligned Terminal Price Bar 时钟后再继续扩展。
- M4：Frontier / Activation / Lifecycle 的形成中实时追踪与状态机产品化
- M5：Priority + A 股环境层（指数/板块相对强弱、流动性、涨跌停、T+1、ATR、开收盘微观结构等）；只影响执行/可交易性，不改写 Carney identity / source PRZ
- M6：全 A 历史日线建库覆盖收口
- M7：全市场 Scanner
- M8：分钟数据智能缓存
- M9：Agent QA / Visual Regression 完整闭环

## 当前状态（2026-09-16）

三卷书复核发现：标准几何主干和既有研究资产可以保留，但产品/runtime 曾把后验 D 点反应审计与 source-aligned Terminal Price Bar 执行时钟混用，并且 `price_low/high` 的理想收敛核心区存在被误称为完整 PRZ 的风险。5-0 还存在 Volume Two / Volume Three 结构 PRZ 与执行细化尚未完成图例级 reconciliation 的问题。

当前修复分支为 `m2/source-fidelity-repair`：

- 后验 D 时钟与 Terminal Price Bar 执行时钟已强制分离；
- `component envelope`、`ideal convergence core` 与尚待冻结的 `source_prz_*` 已拆层；
- source PRZ 未冻结时，Type-II 一律 fail closed；
- Wilder RSI 辅助确认明确不是 RSI BAMM；
- 5-0 默认从 Engine / Scanner / Workbench 隔离，仅研究显式 opt-in；
- 新增 source-aligned Terminal Bar + PEZ 核心契约；
- 正在建立三卷书 Book Golden Ledger，并逐形态冻结可执行 Source PRZ。

历史 45 股 Holdout、独立 60 股外部复现及既有前瞻登记继续作为已经消费/冻结的历史研究记录保存，不回头篡改。若 Source Fidelity Repair 改变未来候选资格或执行定义，应建立新的版本化前瞻协议，而不是改写旧结果。

M2 本地统一验收入口仍为 `运行M2综合验收.bat`。前瞻登记是独立持续研究流程：先完成 M1 日线更新，再运行 `运行M2前瞻Type-I登记.bat`；该流程不执行 interim significance test，也不输出动态“胜率”。