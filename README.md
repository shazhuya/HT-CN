# HT-CN Local

HT-CN 是一个面向中国 A 股实战的本地优先谐波交易研究与辅助决策系统。

## 核心原则

- 本地优先：核心功能在 Windows 本地运行。
- 零订阅：核心功能不依赖付费 SaaS、付费 API、云数据库或 TradingView 会员。
- 方法论可追溯：以 Scott M. Carney《Harmonic Trading》Volume One / Two / Three 为理论基准，并将 A 股增强规则与原始规则分层管理。
- Agent First：从第一版开始具备自动测试、回归测试、浏览器自动化、截图与调试数据输出能力。
- 数据源可替换：市场数据通过 Adapter 层接入，避免绑定单一免费数据源。
- 交易辅助：系统只辅助研究和决策，不执行交易。

## 初始技术栈

- Core / Data / API: Python 3.12 + FastAPI
- Web: React + TypeScript + Vite
- Chart: TradingView Lightweight Charts
- Storage: DuckDB + Parquet
- Testing: pytest + Playwright
- Version control: Git + GitHub

## 里程碑

- M0：工程骨架、本地启动、自动测试基础设施
- M1：A 股数据层、证券主表、日线与增量更新
- M2：Pivot / Fibonacci / Pattern / PRZ Core
- M3：Web K 线与 XABCD / PRZ 可视化
- M4：Frontier / Activation / Lifecycle
- M5：Priority + A 股环境层
- M6：全 A 历史日线建库
- M7：Scanner
- M8：分钟数据智能缓存
- M9：Agent QA / Visual Regression 完整闭环

> 当前状态：M0 启动。
