# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `0c7799391bc92af46a2b249892dc24e06a6143a0`
context_checkpoint_title: `M2.31: Source-Terminal RSI BAMM Phase 4 frozen acceptance`
context_snapshot_date: `2026-09-17`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD`，再继续开发。

## 当前阶段

**M2 Source Fidelity Gate 已完成 M2.31 收口。下一主线进入 M3 Source-Clock Lifecycle Migration。**

M3 Phase 1 既有中文 workbench / lifecycle navigator / browser acceptance 资产继续保留，但不得继续以 retrospective D/C pivot 作为 live execution 时钟。新的产品状态链必须以当时可观察的 Source Raw PRZ / Source Terminal Price Bar 为核心。

截至 M2.31，已冻结：

- M2.27：标准 XABCD Source Raw PRZ Golden Profiles；
- M2.28：standalone AB=CD Source Raw PRZ；
- M2.29：5-0 Volume Two structural PRZ 与 Volume Three execution refinement 分层，production quarantine 保持；
- M2.30：Shark Source Raw PRZ / Terminal Price Bar / reaction management；
- M2.31：独立 RSI BAMM no-lookahead state machine、Volume Two X-A Confirmation Point、Volume Three 四类 profile、Source-Terminal confluence、lifecycle evidence channel 与 45 股 observability。

## M2.31 冻结结论

### RSI BAMM

- 普通 Wilder RSI 30/70 lifecycle evidence 永久不是 RSI BAMM；
- RSI BAMM 使用独立 no-lookahead 状态机；
- RSI(14)，bull <30 / bear >70；
- 两次 distinct extreme tests，中间必须达到 RSI 50 midpoint reaction；
- 第二次 extreme test 必须 impulsive；
- Volume Three 四类 profile：Simple/Complex × Confirmation/Divergence；
- Volume Two Confirmation Point 使用 X-A projection 与 1.13/1.618 source selection；
- complex W/M bar-by-bar classifier 是 HT-CN engineering operationalization，不得伪装成 Carney 原书逐 bar 算法。

### Completed confluence 的正式时钟

历史/right-confirmed D/C 只属于 geometry clock。生产 lifecycle BAMM confluence 不再把历史 D/C 当 Terminal Price Bar。

正式流程：

`pre-terminal pivot observable time -> Source Raw PRZ entry -> Source Terminal Price Bar -> PEZ -> T+1 -> Type-I / Type-II lifecycle`

completed match 通过 `observe_source_execution_for_match()` 重建当时可观察的 source clock，再由 `confirm_rsi_bamm_with_source_execution()` 绑定 BAMM。

合法 Terminal Price Bar 可以形成超出静态 Raw PRZ terminal number 的 PEZ overspill；overspill 不修改 Source Raw PRZ。

BAMM 完成时间晚于 Source T-Bar 时，证据从 BAMM completion bar 才可用，绝不回填。

### 形态边界继续保持

- BAMM 只能增加 confirmation/execution evidence，不能创建、修改或救活 harmonic identity；
- BAMM 不能修改 Source Raw PRZ；
- 5-0 production quarantine 继续；
- Alternate Bat source conflict 继续 fail closed；
- Shark 是独立 `0-X-A-B-C` contract；
- Type-II production 继续使用 HT-CN Strict Full-Retest 保守定义，不得表述为 Carney 排斥所有 nominal retest。

## M2.31 真实 A 股验收

冻结数据集：`a-share-research-v2-45`；snapshot cutoff `2026-09-15`。

最终 closeout：GitHub Actions run #643 / `35209013814`，validated commit `0c7799391bc92af46a2b249892dc24e06a6143a0`，**deterministic + Web build + Playwright + 45-symbol research 全链 success**。

RSI BAMM observability：

- successful symbols：45 / 45；
- complete BAMM sequences：686；
- completed source-scannable harmonic matches：174；
- source-clock observable matches：128；
- actually observed Source Terminal Price Bars：23；
- strict source-confirmed BAMM + harmonic confluences：2；
- 两个 strict confluence 均来自 standalone AB=CD；其中一个在 T-Bar 当下可用，另一个 BAMM 晚于 T-Bar 完成，因此延后时间戳。

这些数字只代表 **observability**。不得据此估计命中率、收益率、alpha 或当前个股概率；`confirmatory_inference_allowed = false` 保持。

46 / 174 个 historical completed matches 无法从 pre-terminal observable state 重建 source clock，进一步证明 M3 必须迁离 retrospective D-clock UI。

## CI / 研究执行政策

- deterministic + Web + Playwright 是短反馈主门槛；
- 45 股重研究只在明确 `[research]` closeout 提交运行，不再因每个文档/小代码提交重复执行；
- research 使用冻结 snapshot/cache/artifact；
- 分支重研究 concurrency 只保留最新 closeout，旧中间研究可取消；
- 已冻结的 Holdout、external replication、historical closed results 不得因此重算或 relabel；
- timeout 只做失控保险，不能代替性能诊断。

## 当前 Source Truth

机器权威状态：`research/source-fidelity-status-v1.json`

人工 Source Ledger：`specs/m2-book-golden-ledger.md`

M2.31 closeout：`research/m2-31-source-clock-closeout-v1.json`

RSI BAMM spec：`specs/m2-31-rsi-bamm-source-state-machine.md`

出现冲突时优先检查：当前代码/测试 -> machine status -> closeout/spec -> 本文件；任何文档漂移必须显式修复。

## 当前 Gate

`M3 Source-Clock Lifecycle Migration`

原则：**产品界面必须回答“现在在哪、先看什么、下一个关键状态/价格、什么使判断失效”，并且所有这些状态必须来自当时可观察的 source execution clock，而不是事后 D/C 解释。**

目标状态链：

`forming -> approaching_source_prz -> entered_source_prz -> waiting_terminal -> source_terminal_complete -> t_plus_1 -> type_i_early_reaction -> type_i_confirmed / type_i_failed / reaction_only -> type_ii_retest_forming -> type_ii_terminal -> reversal_evidence / invalidated`

RSI BAMM 作为独立 evidence channel 叠加在 lifecycle 上，不拥有 lifecycle，不改变 identity/PRZ。

## 当前仍未完全解决

- M3 旧 retrospective lifecycle overlay 尚未全部迁移为 source-clock semantics；
- standard XABCD per-pattern AB=CD family hard gate 仍可继续 source-backed refinement，但优先级低于 M3 source-clock migration；
- 5-0 Volume Two/Three 标签冲突仍未达到 production source-certification 标准；
- optional BAMM Acceleration Trigger 延后到 M3 source-clock migration 之后；
- 真实 A 股研究仍未证明稳定 alpha；
- M1 全市场覆盖度与 harmonic source correctness 继续分开管理。

## 已冻结长期约束

1. Carney Volume One / Two / Three 是 harmonic identity、source measurement、Reaction vs. Reversal 的理论基准。
2. retrospective geometry clock 与 observable execution clock 永久分离。
3. component envelope、Ideal Core、Source Raw PRZ、Terminal extreme、PEZ 永久分层。
4. identity 不能被 score、统计、A 股上下文、BAMM 或 UI 偏好“救活”。
5. A 股 T+1、涨跌停、ATR、流动性、指数/板块环境只进入 execution / tradability 层。
6. 已消费/冻结 Holdout、external replication、历史 closed results 不得回写。
7. 中文优先；内部枚举/API 标识保持稳定。
8. 默认市场范围 SSE/SZSE；BSE 暂不处理。
9. HT-CN 是研究与辅助决策系统，不执行交易。

## 已完成里程碑

- M0 ✅ 工程骨架、本地启动、测试基础设施。
- M1 ✅ A 股数据层、日线、QFQ/HFQ、智能增量、健康检查。
- M2 ✅ Pivot / Fibonacci / Pattern / AB=CD / Shark / Reaction vs. Reversal / T-Bar 研究基础。
- M2.26 ✅ Source Fidelity Repair 主体。
- M2.27 ✅ 标准 XABCD Source Raw PRZ Golden Profiles。
- M2.28 ✅ standalone AB=CD Source Raw PRZ / v4。
- M2.29 ✅ 5-0 V2 structural PRZ / V3 execution layering / v5，production quarantine 保持。
- M2.30 ✅ Shark Source Raw PRZ + source-aligned management / v6 + research CI resilience。
- M2.31 ✅ RSI BAMM dedicated state machine + Source-Terminal lifecycle evidence + real-A observability。
- M3 Phase 1 ✅ 既有中文 lifecycle/workbench/browser acceptance 资产，现进入 source-clock 语义迁移。

## 下一步唯一主任务

**M3 Source-Clock Lifecycle Migration — Phase 1: canonical lifecycle state contract + workbench adapter。**

第一批必须完成：

1. 建立统一 source-clock lifecycle state enum / payload；
2. 从 existing `execution_clock` 派生当前状态，禁止从 historical D/C 直接派生 live state；
3. Workbench 显示“现在在哪 / 先看哪 / 下一个关键价位 / 失效条件 / 当前等待或可观察动作”；
4. BAMM 只显示为 evidence badge/channel；
5. old retrospective fields 保留兼容但标为 diagnostic；
6. deterministic + Playwright 做 no-backdating / lifecycle transition 回归。

## 当前验收入口

- M2 综合验收：`运行M2综合验收.bat`
- M3 工作台保护性验收：`运行M3工作台验收.bat`
- 前瞻 Type-I 登记：`运行M2前瞻Type-I登记.bat`（独立持续研究流程，普通 acceptance 不得修改）

## 新会话恢复必须核对

- 当前 HEAD 与 `context_checkpoint` 的差异；
- 最近 CI 是否 success；
- `research/source-fidelity-status-v1.json` 是否仍为 M2.31 frozen；
- M3 lifecycle 是否使用 Source Terminal Price Bar 而非 historical D/C；
- 5-0 quarantine / Alternate Bat fail-closed 是否仍保持；
- 是否出现新的 research version boundary；
- 是否有旧聊天结论被当前源码/测试推翻。

完成上述检查后，才能宣称“已恢复 HT-CN 当前现场”。
