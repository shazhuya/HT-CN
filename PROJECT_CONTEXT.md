# HT-CN Project Context — 跨对话权威状态

context_schema: `1`
context_checkpoint: `e0f5d9334544944d00b232752ea0e8cdbf5c5bc8`
context_checkpoint_title: `M2.30: Shark Source Raw PRZ v6 + resilient real-A-share research CI`
context_snapshot_date: `2026-09-17`
default_branch: `main`
repository: `shazhuya/HT-CN`

> 本文件用于恢复“项目现在到底做到哪里”。若本文件与当前 HEAD 冲突，必须先检查 `context_checkpoint..HEAD`，再继续开发。

## 当前阶段

当前主线仍处于 **M2 Source Fidelity Repair / Source PRZ Golden Set 收口阶段**。M3 Phase 1 产品资产保留，但 execution overlay 正常扩张继续受 Source Fidelity Gate 约束。

截至 M2.30，已完成：

- M2.27：标准 XABCD Source Raw PRZ Golden Profiles；
- M2.28：standalone AB=CD Source Raw PRZ；
- M2.29：5-0 Volume Two structural PRZ 与 Volume Three execution refinement 分层；
- M2.30：Shark Source Raw PRZ / Terminal Price Bar / reaction management source freeze，并建立 `m2-source-prz-v6` 研究边界。

## M2.30 冻结结论

### Shark Source Raw PRZ

Shark `0-X-A-B-C` 的 Source Raw PRZ 不使用 synthetic midpoint，也不使用 generic XABCD PRZ。冻结为两条原书 published completion corridors 的几何重叠：

- `0B 0.886–1.13 completion corridor`；
- `AB 1.618–2.24 Extreme Harmonic Impulse corridor`。

若两者不重叠，则 source-aligned execution **fail closed**。`1.13 0B` 保持 outer completion / stop-limit reference，不属于 reaction target。

### Shark reaction management

- source-aligned Terminal Price Bar extreme 作为 observable C completion price；
- initial target = 从 Terminal/C 出发先遇到的 `50% BC` 或 `Reciprocal AB=CD`；
- 若 50% 先到，61.8% BC 作为更宽的 prospective 5-0 management level；
- reaction targets 永久属于 post-completion management，不属于 Shark identity / Source Raw PRZ。

### 5-0 状态

M2.29 的 structural contract 保持：

- Source Raw PRZ = `50% BC retracement + Reciprocal AB=CD`；
- Volume Three 61.8 只属于 execution refinement / stop reference；
- Volume Three 图文标签冲突仍显式保留；
- **production quarantine 继续有效**，不得因 evaluator 已存在而恢复默认 Scanner / Workbench 输出。

## M2.30 真实 A 股 v6 验收

数据集：`a-share-research-v2-45`；snapshot cutoff `2026-09-15`。

GitHub Actions run #603 / `35186542998`：**success**。

- frozen snapshot cache：45 hit / 0 miss；
- real-A-share calibration：约 85 秒；
- forming signals：8244；
- mature Source-Raw-PRZ Terminal events：1499；
- Train / Validation / sealed Holdout：871 / 265 / 328；purged 35；
- Shark terminal events：Train 76 / Validation 26 / sealed Holdout 40；
- terminal statuses：terminal observed 1509；source_prz_unresolved 189；
- Type-I visible robustness：`full_prz_exit_by_t3` 与 `full_prz_exit_by_t5` 通过当前 robustness gate；
- completed-reaction robustness：0 个 robust candidate；
- v6 `confirmatory_inference_allowed = false`；不得把 visible research 写成当前个股概率、机械交易规则或 source rule。

历史 v1/v3/v4/v5、冻结 Holdout 与 external replication 均未重算、未改写、未 relabel。

## CI / 研究韧性状态

M2.30 同时修复真实 A 股研究反复“卡死”的工程根因：

- workflow 增加 `actions: read`，可恢复历史冻结 research artifact；
- cache miss 时成功下载完整 45 股快照后立即写入 GitHub cache；
- 长研究 job 使用独立 concurrency，`cancel-in-progress: false`；
- research timeout 由 40 分钟提升到 90 分钟，仅作为安全余量；
- calibration 使用 `python -u` 实时输出逐股进度；
- deterministic-tests 仍允许取消旧 run，不拖慢短反馈链。

run #603 证明主要性能问题来自快照恢复失败，而非 Shark 核心扫描爆炸：恢复快照后 45 股完整校准约 85 秒。

## 当前 Gate

`Source Fidelity before M3 expansion`

原则：**宁可 unresolved / fail closed，也不允许工程近似伪装成 Carney 原书规则。**

### 已冻结约束

1. Carney Volume One / Two / Three 是 harmonic identity、source measurement、Reaction vs. Reversal 的理论基准。
2. retrospective geometry/D 时钟与 execution/Terminal Price Bar 时钟永久分离。
3. component envelope、Ideal Core、Source Raw PRZ、Terminal extreme、PEZ 永久分层。
4. Type-II 必须完整 retest 原 Raw PRZ terminal side 后再进入确认。
5. 当前 Wilder RSI evidence 不是 RSI BAMM。
6. 5-0 production quarantine 继续有效。
7. Shark 使用 M2.30 专属 Source Raw PRZ 与 first-target contract。
8. identity 不能被 geometry score、统计、A 股上下文或 UI 偏好“救活”。
9. 已消费/冻结 Holdout、external replication、历史 closed results 不得回写。
10. A 股 T+1、涨跌停、ATR、流动性、指数/板块环境只进入 execution / tradability 层，不改写 Carney identity。
11. 中文优先；内部枚举/API 标识保持稳定。
12. 默认市场范围 SSE/SZSE；BSE 暂不处理。
13. HT-CN 是研究与辅助决策系统，不执行交易。

## 当前仍未完全解决

- **RSI BAMM**：尚未建立独立、完整、多步骤、no-lookahead 状态机；
- **5-0**：Volume Three 61.8 图文标签冲突尚未达到 production source-certification 标准，因此继续 quarantine；
- standard XABCD per-pattern AB=CD family hard gate 仍需 source-backed refinement，不能长期只靠宽松通用条件；
- M3 retrospective lifecycle overlay 尚未迁移为 source-aligned live execution-clock semantics；
- M1 全市场覆盖度与核心 harmonic 正确性继续分开管理。

## 下一步唯一主任务

**M2.31 — RSI BAMM Dedicated Source State Machine。**

执行顺序：

1. 重新逐段核对 Carney 三卷中 RSI BAMM 的 source sequence、阈值、触发顺序与失效条件；
2. 明确区分普通 Wilder RSI oversold/overbought evidence 与 RSI BAMM；
3. 建立独立 no-lookahead 状态机，不允许一次 RSI 穿越被命名为 BAMM；
4. 建 Book Golden / negative / temporal-order regression；
5. BAMM 只作为 confirmation / execution evidence，除非原书明确，否则不得改写 harmonic identity / Source Raw PRZ；
6. 完成 deterministic + 真实 A 股可观测性验收后，再决定 Source Fidelity Gate 是否进入 standard-XABCD AB=CD hard-gate refinement 或 M3 live execution overlay migration。

## 已完成里程碑

- M0 ✅ 工程骨架、本地启动、测试基础设施。
- M1 ✅ A 股数据层、日线、QFQ/HFQ、智能增量、健康检查。
- M2 ✅ Pivot / Fibonacci / Pattern / AB=CD / Shark / Reaction vs. Reversal / T-Bar 研究基础。
- M2.26 ✅ Source Fidelity Repair 主体。
- M2.27 ✅ 标准 XABCD Source Raw PRZ Golden Profiles。
- M2.28 ✅ standalone AB=CD Source Raw PRZ / v4。
- M2.29 ✅ 5-0 V2 structural PRZ / V3 execution layering / v5，production quarantine 保持。
- M2.30 ✅ Shark Source Raw PRZ + source-aligned management / v6 + CI research resilience。
- M3 Phase 1 ✅ 中文 lifecycle navigator / workbench / 浏览器自动验收资产；后续扩张受当前 Gate 限制。

## 当前验收入口

- M2 综合验收：`运行M2综合验收.bat`
- M3 Phase 1 工作台保护性验收：`运行M3工作台验收.bat`
- 前瞻 Type-I 登记：`运行M2前瞻Type-I登记.bat`（独立持续研究流程，普通 acceptance 不得修改）

## 新会话恢复必须核对

- 当前 HEAD 与 `context_checkpoint` 的差异；
- 最近 CI 是否 success；
- `specs/m2-30-shark-source-freeze-closeout.md`、`specs/m2-shark-five-zero.md` 与当前源码是否一致；
- 是否出现新的 research version boundary；
- 是否有旧聊天结论被当前源码/测试推翻。

完成上述检查后，才能宣称“已恢复 HT-CN 当前现场”。
