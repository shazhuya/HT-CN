# HT-CN Project Blueprint — 项目总蓝图

blueprint_schema: `3`
status: `authoritative`

## 1. 项目使命

HT-CN 是面向中国 A 股的谐波研究与人工辅助决策系统。方法论以 Scott M. Carney 的 Harmonic Trading Volume One / Two / Three 为 Source Truth，工程层在不篡改 Source Identity、Source Raw PRZ、Source Clock 与 Reaction/Reversal 语义的前提下适配 A 股数据、交易制度、研究证据与人工复盘工作流。

HT-CN 不是自动交易执行器，不以历史回看后的漂亮形态冒充实时可得信息，不用产品评分反向修改谐波身份，也不在前瞻证据不足时宣称胜率、alpha 或盈利能力。

## 2. 永久架构边界

1. Source Harmonic Truth 与 A-share Execution Context 永久分层。
2. Identity 先于 quality/score；非法身份不得被评分救回。
3. Source Raw PRZ 与工程 Ideal Core / Component Envelope / PEZ 分层。
4. Confirmed Pivot Clock 与 observable Source Execution Clock 分层。
5. PRZ 只代表潜在反转区域，不等于 reversal。
6. Type-I Reaction 与 Type-II Reversal 分层。
7. ordinary Wilder RSI 不等于 RSI BAMM。
8. Shark 使用 0-X-A-B-C 拓扑，不发明 D。
9. 5-0 保持 production quarantine，直到 Source conflict 被正式解决。
10. Alternate Bat 保持 fail-closed，直到独立 Source contract 完整冻结。
11. 前瞻研究禁止历史回填、美化 cohort 或重写已消费 evidence。
12. M5/M6 产品层不得拥有或改写 M2/M3/M4 authoritative harmonic/research state。
13. 工具只辅助人工决策，不执行证券交易。

## 3. 项目总里程碑

| Milestone | 目标 | 当前状态 |
| --- | --- | --- |
| M0 | 仓库、工程、测试与规范基座 | complete |
| M1 | A 股数据引擎、DuckDB/Parquet、复权/数据 provenance | established |
| M2 | Carney Source Fidelity / Harmonic Core | core frozen |
| M3 | Canonical Source Lifecycle + A 股 Context + Workbench | integrated |
| M4 | Prospective Evidence / Outcome research architecture | architecture frozen, evidence accumulating |
| M5 | Daily Operator / Review / Portable Delivery | Phase 1–23 integrated |
| M6 | Operational Closeout & Integrity | active |
| M7 | Prospective Evidence Accumulation | planned |
| M8 | Evidence-based Decision Calibration | planned |
| M9 | Stable Research/Product Release | planned |

## 4. 最终产品交互目标 — TradingView 类同步图表工作台

HT-CN 的最终主图必须升级为接近 TradingView 的交互式研究工作台，而不是只生成静态谐波截图或固定 SVG。该目标属于正式产品能力，后续实现不得以“静态图已经能显示 XABCD/PRZ”为完成标准。

### 4.1 当前基线与目标差距

当前 Web 主图仍以 `HarmonicChart.tsx` 自绘 SVG 为主：在重新运行分析、切换标的或切换候选时会重新渲染谐波结构，但尚未形成 TradingView 式统一时间轴/价格轴的拖动、缩放、十字光标和 overlay 同步机制。仓库已引入 `lightweight-charts` 依赖，但“依赖存在”不得被视为本目标已完成。

### 4.2 必须实现的交互语义

1. K 线主图支持鼠标拖动平移、滚轮/触控缩放、价格轴与时间轴缩放、视口复位等连续交互。
2. XABCD / ABCD / 0XABC 的节点、腿线和标签必须绑定 canonical K 线时间/索引与价格坐标；主图平移或缩放时，几何 overlay 与对应 K 线同步移动，不允许视觉漂移。
3. Source Raw PRZ、HT-CN Ideal Core、Component Envelope、PEZ、T1/T2、Source Terminal、T+1、Type-I/Type-II 生命周期事件必须使用同一时间/价格坐标系统并与 K 线同步。
4. 节点标签、比例、PRZ 区域和生命周期标记在缩放后仍须保持可读、可审计；不得因为 viewport transform 改写 Source Identity、Raw PRZ、Source Clock 或生命周期状态。
5. 拖动/缩放本身属于显示坐标变换，**不得因为每一个鼠标像素移动而重新跑谐波识别**。只有在新 K 线到达、历史数据窗口扩展、复权/数据版本变化、标的或参数变化时，才触发增量计算或重新分析。
6. 当分析结果更新时，overlay 必须无缝重新锚定最新 canonical bar/time/price；形成中的结构应随新 K 线演化，未来节点不得提前绘制，已冻结的历史 Source evidence 不得被回看重写。
7. 至少支持十字光标/hover 对齐到当前 K 线，并能同时读取 OHLC、节点身份、比例、PRZ、生命周期和关键价位；信息面板与图中对象必须指向同一 bar/time/price identity。
8. 图表实现应优先复用稳定的交互式 chart engine（现有 `lightweight-charts` 可作为候选基础），但第三方库只负责坐标/交互层，不得拥有或改写 HT-CN harmonic Source truth。
9. 浏览器自动化必须验证 pan / zoom 后 XABCD、PRZ、节点、生命周期与目标线仍与原始 K 线 identity 对齐；不能只验证 DOM 元素“存在”。
10. 最终 M9 Stable Research/Product Release 不得在这一交互能力仍停留于静态 SVG snapshot 时宣称产品主图完成。

### 4.3 “实时”定义

HT-CN 在本目标中的“实时”分为两层：

- **实时渲染联动**：用户拖动或缩放图表时，K 线与所有谐波 overlay 立即在同一坐标系内同步移动；
- **数据驱动实时计算**：当 canonical 市场数据新增/扩展或分析参数改变时，谐波引擎按既定 Source 规则增量或重新计算，并把最新状态推送到主图。

这两者必须分开，避免把 viewport 操作误当成重新识别信号，也避免用静态截图冒充 TradingView 类交互。

## 5. M6 蓝图

### M6.1 — Project OS v2 / Cross-Conversation Lossless Continuity
把项目从“聊天驱动”改成“仓库状态驱动”。建立 Blueprint、machine-readable State、Milestone、Change、Decision、Issue、Attempt、Source Coverage、Release Ledger；任何新会话先恢复项目事实再工作。

### M6.2 — Real Private-M1 Closeout
在正式 main + Phase23 read-only preflight 下完成真实 private-M1 current-market full closeout，并审计 identity-bound artifacts。

### M6.3 — Universe Coverage Contract
严格区分 listed universe、initialized universe、formal-QFQ-ready universe、scanner universe、operator universe；产品不得把 initialized coverage 描述为全 A 股覆盖。

### M6.4 — Repository Governance
清理历史 stacked PR；建立/确认 main server-side required checks 或记录权限 blocker；冻结 warning baseline；确保 formal release 与 post-merge governance 同步。

### M6.5 — Source Coverage Freeze
将三卷书全部关键能力归档为 Supported / Partial / Quarantined / Unsupported，并绑定 Source、spec、代码、测试与 decision。

## 6. M7 以后推进原则

M6 完成后，默认停止横向扩功能。M7 优先积累未回看的 prospective cohort、Source Terminal、Type-I/II、right-censoring、5/10/20 traded-bar MFE/MAE 与市场环境分层。在满足预先冻结的样本和协议之前，不输出真实胜率、alpha 或盈利能力结论。

## 7. 项目事实权威顺序

1. canonical Git history / current source / tests；
2. formal release & CI evidence；
3. `governance/PROJECT_STATE.json`；
4. 本 Blueprint；
5. active Change / Decision / Issue / Source Coverage ledgers；
6. active specs；
7. historical PROJECT_CONTEXT / DECISIONS / SESSION_LOG / PR / commit history；
8. 聊天记忆、旧对话、截图。

任何低层信息不得覆盖高层事实。重要事实不得只存在于聊天中。
