# HT-CN Local

HT-CN 是一个面向中国 A 股实战的本地优先谐波交易研究与辅助决策系统。

## 核心原则

- 本地优先：核心功能在 Windows 本地运行。
- 零订阅：核心功能不依赖付费 SaaS、付费 API、云数据库或 TradingView 会员。
- 方法论可追溯：以 Scott M. Carney《Harmonic Trading》Volume One / Two / Three 为理论基准，并将 A 股增强规则与原始规则分层管理。
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
- M2 ✅ Pivot / Fibonacci / Pattern / PRZ Core，并扩展完成：AB=CD、Shark、5-0、Reaction vs. Reversal、Terminal Price Bar、Type-I/II 证据层、真实 A 股校准、冻结 Holdout / 外部复现、前瞻 Type-I append-only registry
- M3 ▶ 实战工作台产品化：K 线 / XABCD / PRZ / 生命周期的“当前在哪、先看哪、到了再看哪”状态表达、交互与视觉回归收口。M2 已提前具备基础 Web 图表和部分生命周期能力，M3 不重复造轮子。
- M4：Frontier / Activation / Lifecycle 的形成中实时追踪与状态机产品化
- M5：Priority + A 股环境层（指数/板块相对强弱、流动性、涨跌停、T+1、ATR、开收盘微观结构等）；只影响执行/可交易性，不改写 Carney identity / PRZ
- M6：全 A 历史日线建库覆盖收口
- M7：全市场 Scanner
- M8：分钟数据智能缓存
- M9：Agent QA / Visual Regression 完整闭环

## 当前状态（2026-09-16）

M2 开发分支 `m2/harmonic-core` 已进入收口：核心几何、PRZ、生命周期证据链和真实 A 股研究验证均已完成，历史 45 股 Holdout 与独立 60 股外部复现已经冻结并标记 consumed/closed；从 2026-09-16 起只继续追加前瞻 Type-I registry，不再回头搜索历史阈值。

M2 本地统一验收入口：`运行M2综合验收.bat`。前瞻登记是独立的持续研究流程：先完成 M1 日线更新，再运行 `运行M2前瞻Type-I登记.bat`；该流程不执行 interim significance test，也不输出动态“胜率”。
