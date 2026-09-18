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


## M3 Phase 3.2 / 2026-09-18

- Phase 3.1 batch 2 committed at `f5fa0dc39f65d98dc0479b4b62d103263f7b18c3`: automated positive suspension ingestion, non-downgrade storage, sync audit and M1 daily integration.
- Phase 3 UI wiring correction committed at `179601bd39909bf89d23b788dd0b74b294e955cd`: execution-context component is now actually mounted; its Playwright test is now part of CI.
- Phase 3.2 first batch committed at `0effcaffd033d5398ffa0e0b09ab67188a958e58`: local core benchmark store/sync, market-context backend payload, Workbench card and browser regression for STAR50/ChiNext/CSI300/SSE Composite.
- Market context remains evidence-only: no composite score, no identity/Source-PRZ mutation, no lifecycle ownership.
- GitHub-hosted CI still fails before steps/logs; development continues without repeated reruns.


## M3 Phase 3.3 / 2026-09-18

- `686e7ec7af089f3553f6094e27d20cfc4a343aa0`: industry schema, atomic membership refresh, local constituent aggregation, sync script and Windows entrypoint.
- `2c27f45a00c42dcf67da48a0d7f5326356b640b1`: AKShare industry provider normalization and API `sector_context` integration.
- `4fab82c9012dcf19a5c719dbe37d65a19d90b64b`: Workbench industry card.
- `e5ede700ad63774c6c75f5e446cb8b77b7e648b5`: provider/context/browser regression gates and Phase-3.3 spec.
- `8fafdbeff59b818b63c2db83bae3a86e86641eff`: sector browser regression added to CI command.
- `a03d31a12d6f30d4aac1dd4787d27a63cf5afd24`: optional `pct_change` hardening with close-to-close fallback.
- `85b752ce9b3c5fd188a2d09943fd4aa24f618445`: analysis read paths kept side-effect free; sector tables/benchmark directories are no longer created by ordinary reads.
- Industry strength/breadth/volume is recomputed from local M1 constituent data; Eastmoney supplies membership only.
- Multi-industry ambiguity is fail-closed; industry context cannot own lifecycle or mutate identity / Source Raw PRZ.


## M3 Phase 3.4-3.5 / 2026-09-18

- Phase 3.4 adds multi-membership concept/theme context; multiple concepts are normal rather than ambiguous.
- Concept membership refresh uses bounded concurrency + retry and all-or-nothing replacement; partial failures preserve the previous complete mapping.
- Concept evidence is recomputed from local M1 constituents and ordered only by raw 5-day median return; there is no theme score.
- `acc0efee28827e8df979201ddac666601bfd9f7d` prevents industry/concept future membership from backdating into earlier analysis.
- Phase 3.5 adds `context_integrity` with current/partial/stale/missing/conflicted/future_observation/unresolved states and no score.
- Membership older than the default seven-day refresh horizon is surfaced as stale even when a current local aggregate snapshot exists.
- `运行M3上下文数据同步.bat` now performs execution-event, core benchmark, industry and concept sync in one pass and writes a combined machine-readable report.
- Current implementation checkpoint before docs commit: `a08a601568342ca9049923f0b5ee156d8dd96eb8`.


## M3 Phase 4.1-4.3 / 2026-09-18

- `4c7110c5ed11a98a6730fbdd1ade0b442f2c0c97`: product payload contract auditor.
- `12032dc56ad68beeede7930d9878aede45ef8220`: real-M1 product-contract smoke + upgraded one-click acceptance.
- `dcdcd8e5c1099f5892ad8fdec565c7dd43ae7d00`: selected-pattern narrative browser consistency gate + Phase-4 spec.
- `a8d94554da20e50f8a7e3c82c0f97fec38517539`: source-driven LifecycleCompass consolidated into Source Clock evidence strip.
- `0eb48487564fdbdbb2db7eb181f0ebde1b61580c`: formal acceptance now requires readable real parquet histories.
- `12e853581970b0d259acb35a5beaecdb1ff19e63`: lifecycle action state separated from execution feasibility gate.
- `9326ca7fdb0cacf20d08a987a3d447ada17f9621`: product-contract fixtures and browser execution-gate assertion aligned.
- Formal action-state vocabulary is waiting / reaction_observation / execution_evaluation / evidence_insufficient.
- Context cannot vote on or override source lifecycle; execution feasibility is reported separately.
- PR stays Draft until user-local real-M1 acceptance and context-sync evidence are observed.


## M3 Phase 4.4 / 2026-09-18

- `7a60bbbba9effe525b1ffb217aa1458ea37b0ba5`: fixed context-sync success literal / exit-code mismatch.
- `63fa707d78b1d796d5c1174a1dafa3c4ba5b8a94`: acceptance, metadata, product and context reports now stamp exact git HEAD.
- `a1525389f088257563a88c1f26558ad98b0b0967`: machine-readable PR readiness evaluator + merge-readiness and final-closeout Windows entrypoints.
- `9f95560b3d44b5eb70c4f40cc3d5e9c72471d285`: human-readable Chinese readiness report added.
- Readiness hard-blocks stale evidence from old commits.
- Context partial failure is blocker; fail-safe degraded refresh is visible warning.
- Positive-evidence-only suspension coverage remains a known warning and does not masquerade as complete-market evidence.
- Code-side Phase 4.4 closeout is complete; user-local real-M1 evidence remains to be generated before PR #12 can leave Draft.


## M3 Phase 4.5 / 2026-09-18

- `33144a937360fa8cfce009c618b947da8a40d88c`: centralized provider-backed latest closed-trade clock; M1 updater now persists confirmed calendar dates.
- `9e3b1ed8643c2cb64f2fc6418eb19101170654a0`: formal metadata smoke switched from base-only parquet to base+daily_delta logical history.
- `4b0488f557578f1c50b3aa67c88f9938479faf3b`: context sync compares provider-confirmed expected closed day with local calendar/logical market date.
- `ba75cb2e577458e6e48384fab51bc5c7ea52d4ed`: metadata/product/context evidence must align to one expected trade date; final closeout now starts with M1 smart daily update.
- `3c4ed222b8002d7455ff687a48210d7b1052a440`: all initialized listed SSE/SZSE datasets must be current; any stale/ahead dataset blocks Ready.
- `181c86c27cfbf25db69f1579f86c45dfb52fc1a0`: clean-worktree evidence identity added.
- `26c1f171b95830bfd06923591bd959e83e659c27`: formal reports and readiness bound to clean worktree state.
- `b536dd944e6f9b541506619fd7bd851b72bb732e`: readiness/freshness fixtures aligned with final anti-false-green contract.
- Phase 4.5 changes acceptance only; harmonic identity / Source PRZ / lifecycle semantics remain unchanged.


## M3 Phase 4.6 / 2026-09-18

- User-local closeout on `c444ac64...` confirmed M1 updated 55/55 initialized datasets to 2026-09-17 with zero stale/ahead datasets.
- Real run exposed `artifacts/` as untracked, causing QA to stop before deterministic gates; fixed by ignoring `artifacts/**`.
- Final Windows closeout wrapper headings were parsed incorrectly on CMD; control/output lines are now ASCII-safe.
- External Eastmoney/AkShare disconnects are now classified separately from local structural failures.
- Industry/concept external unavailability becomes explicit degraded warning; local schema/aggregate/program failures remain blockers.
- Degraded external-only context sync now exits 0; structural partial failure remains non-zero.
- Readiness tests freeze READY-with-warnings for external-unavailable context and NOT READY for local failed context.
- Current implementation checkpoint before docs commit: `ce90d575009b658a6a6c3a1d33b21cf107ce54cd`.


## M3 Phase 4.7 / 2026-09-18

Second user-local closeout on `28488826...` proved:
- M1 fast-pass current: 55/55 initialized datasets already at 2026-09-17;
- worktree clean fix worked;
- context external-unavailable semantics worked: context exit 0 with explicit warnings;
- remaining blockers were exclusively deterministic pytest regression drift.

Five repairs:
- context sync exit-contract test updated for degraded nonblocking semantics;
- frozen external replication hash verification normalized checkout CRLF to canonical LF; canonical SHA verified as `4116aeaae8e783f2f5ebc244a001cf78b407cd39b5265eae4e24906c3b819f09`;
- continuity sentinel phrase restored;
- API health test aligned to version 0.3.0;
- Golden Ledger now explicitly names Source Terminal Price Bar.

`.gitattributes` now enforces LF for JSON/Markdown/Python to reduce future Windows hash drift.
Implementation checkpoint: `5a301baf848d740a537b2b07032057dd566309f9`.
