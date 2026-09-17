# HT-CN Session Log — 会话交接记录

本文件只记录每个开发 Session 最后停在哪里。详细技术事实仍以源码、测试、`PROJECT_CONTEXT.md`、`DECISIONS.md`、`specs/` 为准。

## 2026-09-17 — M2.31 RSI BAMM Source-Terminal Phase 4 收口

### 基线

- 起始 main：`0537d0222db5ed4a0ea3f69369dfcb31ee0dbca1`（M2.30 formal release）
- 最终研究验收检查点：`0c7799391bc92af46a2b249892dc24e06a6143a0`
- 分支：`m2/rsi-bamm-source-state-machine`
- PR：#11 `M2.31: RSI BAMM source state machine and lifecycle evidence`
- 最终全链 CI：run #643 / `35209013814`，deterministic + Web + Playwright + 45-symbol frozen research **success**

### 完成

- 建立独立 RSI BAMM no-lookahead 状态机；
- 冻结 Volume Two Trigger / midpoint / X-A Confirmation Point / 1.13 vs 1.618 source selection；
- 冻结 Volume Three Simple/Complex × Confirmation/Divergence 四类 profile；
- complex W/M classifier 明确标记为 HT-CN engineering operationalization；
- BAMM 明确为 confirmation/execution evidence only，不得修改 harmonic identity / Source Raw PRZ；
- Phase 3 geometry-terminal adapter 保留兼容/golden-test；
- Phase 4 新增 `observe_source_execution_for_match()` + `confirm_rsi_bamm_with_source_execution()`，正式绑定 Source Terminal Price Bar；
- 修复 historical D/C 被误当 Source T-Bar 的生命周期语义问题；
- 支持合法 PEZ overspill，同时保持 static Source Raw PRZ 不变；
- BAMM completion 晚于 Source T-Bar 时禁止 backdate；
- lifecycle 增加独立 BAMM evidence channel；
- 新增 machine-readable Source Truth `research/source-fidelity-status-v1.json`；
- `m2-book-golden-ledger.md` 升级到 M2.31，修复 M2.26 之后的状态漂移；
- Type-II 文档明确：full Source Raw PRZ retest 是 HT-CN strict production policy，不等于 Carney 排斥 nominal retest；
- 5-0 quarantine 与 Alternate Bat fail-closed 保持；
- CI 调整为 ordinary deterministic/browser + `[research]` closeout 才运行 45 股重研究；旧中间研究可取消。

### 45 股 frozen observability

数据集：`a-share-research-v2-45`，snapshot cutoff `2026-09-15`。

- successful symbols：45 / 45；
- RSI BAMM sequences：686；
- completed source-scannable harmonic matches：174；
- source-clock observable matches：128；
- observed Source Terminal Price Bars：23；
- strict source-confirmed BAMM/harmonic confluences：2；
- 两个 strict confluence 均为 standalone AB=CD；
- 一个在 Source T-Bar 时已经可用；另一个 BAMM 后完成，因此 evidence timestamp 延后；
- `confirmatory_inference_allowed = false`；此报告不支持命中率/alpha/当前个股概率推断。

### 关键发现

最初 geometry-terminal observability 得到 `source_confirmed=0`。核查发现 Phase 3 adapter 仍以 `match.points[-1]` 的历史 D/C 作为 terminal。修复为 Source Terminal Price Bar 之后，正式结果为 2 个 strict confluence。

这个过程证明：历史 completed geometry 与 live execution observability 不是同一件事。174 个 historical completed matches 中只有 128 个能从 pre-terminal observable state 重建 source clock，因此 M3 必须迁离 retrospective D-clock。

### 关键决定

- D-018：completed BAMM confluence 必须绑定 Source Terminal Price Bar；
- D-019：45 股重研究只由明确 closeout 触发，分支只保留最新 closeout；
- D-020：M3 live/current lifecycle 必须由 source execution clock 驱动。

### 未解决

- M3 旧 retrospective lifecycle overlay 还没完成 source-clock migration；
- 5-0 V2/V3 label conflict 继续 production quarantine；
- standard XABCD per-pattern AB=CD hard-gate refinement 尚可继续，但低于 M3 migration 优先级；
- optional BAMM Acceleration Trigger 延后；
- 尚无稳定 alpha 证明。

### 下一步唯一主任务

**M3 Source-Clock Lifecycle Migration — canonical state contract + Workbench adapter。**

第一批：

1. 建 unified source-clock lifecycle state enum/payload；
2. current state 只由 observable execution_clock 派生；
3. Workbench 中文显示“现在在哪 / 先看哪 / 下一关键价位 / 失效条件 / 当前动作”；
4. BAMM 只作为 evidence badge；
5. old retrospective D/C field 标记 diagnostic/compatibility；
6. 加 deterministic + Playwright transition/no-backdating regression。

### 新会话特别注意

- M2.31 已完成，不得再把 RSI BAMM 写成“尚未建立”；
- `confirm_rsi_bamm_with_match()` 不是 production lifecycle canonical clock；
- production confluence 使用 Source Terminal Price Bar；
- PEZ overspill 合法但不能反写 Raw PRZ；
- 45 股 2 个 strict confluence 是 observability，不是胜率/收益结论；
- M3 不要继续堆新形态，先完成 source-clock lifecycle 产品迁移。

---

## 2026-09-17 — M2.30 Shark Source Raw PRZ / v6 收口

### 基线

- 起始 main：`6d36dfe4c9e2b597df80596ad1bb1c08d286e9f0`（M2.29 merge）
- 结束功能/研究检查点：`e0f5d9334544944d00b232752ea0e8cdbf5c5bc8`
- 分支：`m2/shark-terminal-source-freeze`
- CI：run #603 / `35186542998`，deterministic + Playwright + 45-symbol real-A-share v6 全链 **success**

### 完成

- Shark Source Raw PRZ 冻结为 `0B 0.886–1.13` corridor 与 `AB 1.618–2.24` corridor 的几何 overlap；
- 新增 Shark source contract / Book Golden evidence / negative regression；
- source-aligned Terminal Price Bar 支持 Shark；
- Shark reaction management 使用 first encountered of `50% BC` / `Reciprocal AB=CD`；61.8% BC 保持 wider prospective 5-0 level；
- 5-0 M2.29 structural semantics 保持，production quarantine 未解除；
- research definition 升至 `m2-source-prz-v6`；
- 新增 v6 sealed research guard；
- 修复旧 `specs/m2-shark-five-zero.md` 的 5-0 50–61.8 universal-band 漂移；
- CI 修复 Actions artifact 权限、snapshot bootstrap、即时 cache、90 分钟安全 timeout、实时无缓冲进度输出。

### 真实研究验收

- cache：45 hit / 0 miss；
- 45 股 calibration：约 85 秒；
- forming signals：8244；
- mature Source-Raw-PRZ Terminal events：1499；
- Train / Validation / sealed Holdout：871 / 265 / 328；purged 35；
- Shark Terminal events：76 / 26 / 40；
- Type-I visible robustness：`full_prz_exit_by_t3`、`full_prz_exit_by_t5`；
- completed-reaction robustness：none；
- v6 confirmatory inference：false；
- historical v1/v3/v4/v5 / Holdout / external replication 未重算、未 relabel。

### 关键决定

- D-015：Shark Source Raw PRZ = published source corridors geometric overlap；
- D-016：真实 A 股长研究必须 snapshot-first、resumable、observable。

### 下一步

后续已由 M2.31 继续推进。

---

## 2026-09-17 — M2.28 Standalone AB=CD Source Raw PRZ 收口

### 基线

- 起始功能检查点：`612c0dc01ecbbadfe763bbe9a78c9acd9cee5014`（M2.27 merge）
- 结束功能/研究检查点：`07fde2b1d69664e421b1cb86e3af45a6e26b1093`
- 同步 main 双父 merge：`2a8bbdf318c28a5fce9f350d88abc849f8e37203`
- 分支：`m2/source-prz-abcd`
- CI：run #555 / `35127486034`，deterministic + real 45-symbol A-share research 全链 success

### 完成

- standalone AB=CD Source Raw PRZ：equivalent `AB=CD x1` defining completion + reciprocal BC；
- Volume Three BC layering 固定为 execution-only，不进入 identity / Raw PRZ；
- SourceAligned API 升至 semantics v3 / source profile v2；
- 新增 AB=CD Book Source ledger / Golden regression；
- research definition升至 `m2-source-prz-v4`；
- 新增 v4 sealed research boundary guard；
- 历史 v1/v3/Holdout/external replication 均保持不可变。

### 下一步

后续已由 M2.29 / M2.30 / M2.31 继续推进。

---

## 2026-09-17 — 建立跨对话无损续接机制

### 基线

- 仓库：`shazhuya/HT-CN`
- 默认分支：`main`
- 功能/研究检查点：`612c0dc01ecbbadfe763bbe9a78c9acd9cee5014`

### 本 Session 完成

- 新增 `AGENTS.md`、`PROJECT_CONTEXT.md`、`DECISIONS.md`、本 `SESSION_LOG.md`；
- 新增 context pack 与 Windows 一键检查/生成入口；
- 后续任何新会话必须检查 `context_checkpoint..HEAD`，禁止仅依赖旧聊天记忆。

---

## Closeout 模板

```text
## YYYY-MM-DD — Session 标题

### 基线
- 起始 HEAD：
- 结束功能/研究检查点：
- 分支：
- CI：

### 完成
- 

### 关键决定
- 无 / 见 D-XXX

### 验收
- 

### 未解决
- 

### 下一步唯一主任务
- 

### 新会话特别注意
- 
```
