# HT-CN

HT-CN 是面向中国 A 股的本地优先谐波研究与人工辅助决策系统。方法论以 Scott M. Carney 的 *Harmonic Trading* Volume One、Volume Two、Volume Three 为 Source Truth，并在不改写 Source Identity、Source Raw PRZ、Source Clock 与 Reaction/Reversal 语义的前提下接入 A 股数据、市场制度、研究证据和复盘工作流。

本项目不执行证券交易，不用评分救回非法谐波身份，也不在前瞻证据不足时宣称胜率、Alpha 或盈利能力。

## 当前状态

- 当前里程碑：**M6.2 — Real Private-M1 Closeout**；
- 工程状态：M6.2 实现和正式主线 CI 已完成；
- 真实状态：`awaiting_private_run`，真实私有 M1 最终证据尚未生成；
- 当前唯一收口入口：`运行HT-CN M6.2真实Private-M1最终收口.bat`；
- 预期唯一上传物：`artifacts/reports/htcn-m6-private-m1-closeout-evidence.zip`；
- 原始 M1 数据、Parquet、DuckDB 和 daily delta 不上传；
- 5-0 保持生产隔离，Alternate Bat 保持失败关闭，HSI 未支持。

权威实时状态在 [`governance/PROJECT_STATE.json`](governance/PROJECT_STATE.json)。旧聊天和 `PROJECT_CONTEXT.md` 不能覆盖当前 Git、测试、正式 CI 与 Project State。

## 架构边界

1. Source Harmonic Truth 与 A-share Execution Context 分层；
2. Identity 先于 quality/score；
3. Source Raw PRZ 与 Ideal Core / Component Envelope / PEZ 分层；
4. Confirmed Pivot Clock 与 observable Source Execution Clock 分层；
5. PRZ 代表潜在反转区域，不等于已经反转；
6. Type-I Reaction 与 Type-II Reversal 分层；
7. ordinary Wilder RSI 不等于 RSI BAMM；
8. Shark 使用 0-X-A-B-C，不发明 D；
9. M4 前瞻研究和 Outcome Engine 不得被产品开发改写；
10. 系统只提供研究和人工复盘，不自动下单。

完整蓝图见 [`PROJECT_BLUEPRINT.md`](PROJECT_BLUEPRINT.md)，Agent 续接规则见 [`AGENTS.md`](AGENTS.md)。

## 目录

| 路径 | 职责 |
|---|---|
| `src/htcn/harmonic/` | 谐波身份、比例、PRZ 和核心模型 |
| `src/htcn/data/` | A 股数据、复权、校验与存储 |
| `src/htcn/research/` | 冻结研究协议和结果评估 |
| `src/htcn/app/` | 日常操作、交接、复盘与便携交付 |
| `apps/web/` | React/TypeScript 本地工作台 |
| `scripts/` | 数据、研究、产品、验收和 Project OS 入口 |
| `specs/` | 各阶段冻结规范 |
| `governance/` | Project State、Change、Decision、Issue、Attempt、Source Coverage 和质量基线 |
| `tests/` | Python 回归测试 |

## Windows 用户入口

首次安装：

```text
安装HT-CN.bat
```

启动本地工作台：

```text
启动HT-CN.bat
```

检查当前项目续接状态：

```text
检查HT-CN续接状态.bat
```

生成动态续接包：

```text
生成HT-CN续接包.bat
```

当前 M6.2 真实私有收口：

```text
运行HT-CN M6.2真实Private-M1最终收口.bat
```

该入口不得自动安装依赖、拉取或重置 Git、修复行情数据或安装浏览器。任何失败必须保留证据并进入 Attempt Ledger，不能静默修改后伪装成一次成功运行。

## 开发环境

要求：

- Python `>=3.13,<3.14`；
- Node.js 22；
- Windows 是真实私有 M1 收口的当前操作环境；
- Linux/CI 可验证确定性代码、夹具、浏览器和冻结守卫，但不能声称完成私有 M1 实跑。

Python：

```bash
python -m pip install -r requirements-dev.lock
python -m pip install --no-deps -e .
python scripts/project_state.py
python scripts/ruff_with_budget.py
python scripts/pytest_with_warning_budget.py
```

也可以使用锁定环境：

```bash
uv sync --locked --all-extras --python 3.13
```

Web：

```bash
cd apps/web
npm ci
npm run build
```

质量门禁：

- Project OS 状态必须一致；
- Python 测试必须通过；
- Python warnings 当前冻结上限为 1163，只允许下降，不允许无变更记录地增加；
- Ruff 历史债务当前冻结上限为 485，只允许下降；新增和实质修改的 Python 文件必须保持干净；
- Web 必须构建成功；
- 正式主线运行浏览器验收、Phase18、Phase21、M4 methodology freeze 和 Outcome Engine freeze；
- 托管 fixture 只证明机制，不能代替真实市场或私有 M1 证据。

## Project OS 工作规则

开始任何非琐碎工作前：

```bash
git fetch --all --tags --prune
python scripts/project_state.py --resume
```

然后依次读取：

1. `governance/PROJECT_STATE.json`；
2. `PROJECT_BLUEPRINT.md`；
3. 当前 active Change；
4. Decision、Issue、Attempt、Source Coverage 和质量台账；
5. `required_specs` 中与当前 Gate 有关的规范。

任何 state / Git / ledger 不一致必须先修复。每一次有意义的失败、修复、验证、合并和真实运行结果都必须写入仓库，不能只留在聊天中。

## 数据边界

- `data/`、`artifacts/`、本地数据库和运行日志不属于源代码交付；
- 私有 M1 原始行情不得提交；
- 正式证据通过哈希和身份链验证；
- 公开 CI 使用确定性夹具，不接触用户私有数据库；
- 产品中的 “universe” 当前指本地已初始化数据集，不能无条件解释成完整 A 股市场。

## Source 支持状态

| 能力 | 状态 |
|---|---|
| AB=CD | supported |
| Gartley / Bat / Butterfly / Crab / Deep Crab | supported_frozen |
| Shark | supported_frozen，0XABC |
| 5-0 | quarantined |
| Alternate Bat | fail_closed |
| RSI BAMM | supported_source_state_machine |
| Type I / Type II | supported_source_clock |
| HSI | unsupported |

机器可读明细见 [`governance/SOURCE_COVERAGE.json`](governance/SOURCE_COVERAGE.json)。`supported_frozen` 当前不自动等于每一幅原书图都已经完成坐标级回归。

## 贡献边界

任何修改不得：

- 用分数或 A 股经验改写 Carney 身份规则；
- 把 retrospective D 冒充实时可观察 Terminal；
- 为 Shark 虚构 D；
- 解除 5-0 隔离或 Alternate Bat 失败关闭而没有新 Source Decision；
- 把普通 RSI 叫作 RSI BAMM；
- 改写已冻结的 M4 方法或已消费的前瞻证据；
- 从历史关联推导胜率、Alpha、盈利能力或自动交易结论。

非琐碎修改需要 CR，所有验证尝试需要进入 append-only Attempt Ledger。完整规则以 [`AGENTS.md`](AGENTS.md) 为准。
