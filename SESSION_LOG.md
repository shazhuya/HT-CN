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


## M3 Phase 4.8 / 2026-09-18

Third user-local closeout on `8986897924ba64e2e6c85b26393c84258d7ce1a7` proved:
- deterministic Python: 376 passed;
- Web TypeScript/Vite build: passed;
- strict real-M1 metadata/tradability: passed;
- product smoke: 8/8 analyses succeeded, 10 patterns observed, 2 contract issues only;
- both issues were forming Shark patterns missing canonical `source_lifecycle`;
- context degradation remained warning-only as designed.

Root cause:
- completed Shark had a dedicated source-clock reconstruction path;
- forming Shark payload had schema `0XABC`, while forming execution-clock adapter accepted only XABCD/ABCD;
- therefore no `execution_clock.lifecycle` existed to promote into `source_lifecycle`.

Fix:
- forming `0XABC` now uses Source Raw PRZ execution observation after B confirmation;
- reaction anchor is B for Shark, A for XABCD/ABCD;
- completed Shark source reconstruction also uses B, aligning Type-I reaction span with B→C/T-Bar;
- no D point is introduced;
- execution clock carries explicit Shark management evidence: 50% BC, 61.8% BC, Reciprocal AB=CD, and first-of-50%-or-reciprocal initial target;
- generic Type-I 38.2/61.8 is labeled confirmation evidence only, not Shark management.

Implementation checkpoints:
- `7f142a78de9dc671a8d1385493018c681e845526` — forming Shark canonical source lifecycle.
- `b4b18f555dec47a4cbfbe63d1777aa85c30f0e3a` — Shark-specific management preserved on source clock.


## M3 Phase 4.8.1 / 2026-09-18

Fourth user-local closeout on `81d92557493b8874b040f6142e9d416ea6ae619e` stopped at one new Shark lifecycle regression assertion:
- implementation returned 50% BC target 110.44;
- Reciprocal AB=CD was 110.88;
- frozen Shark rule is first encountered of 50% BC and Reciprocal AB=CD;
- therefore implementation was correct and the test expectation was wrong.

Fix commit: `105a08ddfc4cef16a22e8504fd4c289fe2eb0c2f`.
No harmonic logic, Source Raw PRZ, lifecycle semantics, or management formulas were changed.


## M3 Phase 4.9 / 2026-09-18

Fifth user-local closeout on `c6c9514647fadf50bf08e00c0cc58bbbb886c330` reached the final browser layer:
- Python regression passed;
- Web build passed;
- strict real-M1 metadata passed;
- real-M1 product contract passed;
- local services started;
- Playwright result: 15 passed / 3 failed.

The three failures were stale browser assertions:
- execution-context still expected pre-Phase-4 LifecycleCompass copy;
- live test still expected API 0.2.0 instead of 0.3.0;
- fixture smoke still expected an old retrospective note removed during UI consolidation.

No Source lifecycle, harmonic identity, Source Raw PRZ, Shark management or execution-context production logic was changed.
Implementation fix commit: `d28215bbae682169a8ac47ddf48399bfdf50d05a`.


## 2026-09-18 — M3 formal merge / M4 Phase 1 start

### M3 正式合并
- PR #12 已从 Draft 切到 Ready 并正式 merge；
- merge commit：`edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25`；
- merge 前 branch vs main：ahead 85 / behind 0；
- unresolved review threads：0；
- 本机 current-head readiness：READY with known warnings，hard blocker=0；
- GitHub-hosted Actions 仍存在 steps/logs 为空的 runner-allocation 异常，不作为实际测试执行。

### M4 新分支
- branch：`m4/real-a-share-validation-workflow`；
- base：M3 merge commit；
- 目标：先做真实 A 股 prospective lifecycle evidence，不直接做新 pattern 或黑箱评分。

### M4 Phase 1 第一批
- `d737ee73bccb5086dfbbcaa08d42e9b490dca376`：append-only lifecycle journal contract；
- `4922cca8c9dea41551d3cbeeb8e722eafbf2589f`：全市场一键 prospective snapshot；
- 稳定 key 用 anchor trade_date，防 rolling-window index 漂移；
- journal 默认禁止 backfill；
- 5-0 继续排除；
- snapshot 只有在全部 selected initialized SSE/SZSE 分析成功且日期一致时才追加；
- `alpha_inference_allowed=false`。

### 下一步唯一主任务
在用户真实 M1 数据上生成 M4 T0 prospective snapshot。


## M4 Phase 1.4 / 2026-09-18

User corrected workflow: assistant must not use the user's PC as a routine test runner. D-023 is frozen.

Assistant-side review of uploaded T0:
- snapshot status pass;
- 55/55 instruments successful;
- 87 unique candidates;
- single HEAD / single as-of date;
- no 5-0;
- no alpha inference / trade instruction;
- 11 rows already had a Source Terminal date before T0;
- therefore T0 is baseline inventory, not from-formation prospective evidence.

Implementation:
- `43822e3e441850d0b0e79320cec14542b5187377`: baseline_existing vs prospective_new enrollment;
- `506f38be16199346eced18f94702c905067b3b95`: factual transition engine;
- `3b2975a86aede8ae1597de8c2dcc5e2466b2d154`: scanner reappearance identity preservation;
- `3c1fc9f2fc25b44b32f87a3ce6c92b3a90405f35`: derived transition report;
- `d84de859af666b25e2c623ebfc736805d31e89b0`: prospective outcome eligibility isolated from generic validation;
- `4096e19ceb586df0a48d144cb09b07dc7b85ca1c`: transition report exposes outcome-eligible row count.

Current T0 normalization:
- baseline_existing = 87;
- prospective_outcome_eligible = 0;
- no transition/outcome claim is permitted yet.


## M4 Phase 1.5-1.6 / 2026-09-18

Assistant-side T0 quality audit and outcome-cohort hardening:

- `d014c4f424390edd21a219bfc54061aa4068260e`: strict prospective outcome gate at journal append;
- `c645d0405e643e024ca7504a162037292d8b712a`: transition normalization uses same outcome gate;
- `d672de8288a972046cb3d1ca8a4cb0d41d9009d8`: regression coverage for Alternate Bat / pre-terminal enrollment / delayed resolution;
- `ed1552abbe5694fe8c786460372c972c2a754e2d`: T0 baseline audit engine;
- `7518749476b97bc0315b0f15510a6d4594a006a5`: derived JSON/Markdown T0 audit report;
- `f0bc64b8b8aabaa4981c565207d7afd1b2854ce4`: strict snapshot-journal cross-file/maturity gate;
- `880f81b700b54f15ccc42344f30f6f3eadcfe9b2`: audit regression fixtures aligned;
- `704bf2f6032608ab2e710fe4805ba2127c69f3ac`: linear-time outcome-enrollment normalization.

Actual uploaded T0 audit:
- 87 rows / 87 unique keys;
- 55/55 instrument capture pass;
- 0 structural blocker;
- 6 explicit warnings;
- transition_ready=true;
- prospective_outcome_ready=false;
- AB=CD concentration 56/87 = 64.4%;
- 11 rows already post-terminal at T0; oldest terminal age 583 days;
- 13 source-observability-gap rows;
- all action/next-key/PRZ/terminal/source-fidelity contracts internally consistent.

D-024 freezes strict outcome enrollment: prospective_new alone is insufficient.


## M4 Phase 2.1-2.4 / 2026-09-18

Assistant-only implementation; no user-local QA.

- `2ce430a9e512c8174b63a2ed5635281f061aa9eb`: future journal rows persist raw OHLC/volume;
- `3dd8c1b4679d9422ca2ba4522097438b2881c8be`: raw market-fact regression;
- `f3d4e02e8dfff9387f8c83666413aad9f1e73cf9`: public normalized journal view;
- `62ea3b16c7fd1fa735c8f78bbd2c99a5136e7567`: prospective observation panel;
- `0c04d9821917a51421bc10579b9223e224dafff0`: one code head per capture date;
- `25f09983747a1163f20e9ccfe6bc73599ce1dadb`: append-only snapshot manifest;
- `b24db0496a1e36db0331857284dbfe5e1c209909`: capture pipeline writes manifest;
- `c5de30af208f4a7099ba8d017c2ac0f4760ffc9c`: authoritative capture timeline resolver;
- `2d58e8bdead6e2dcc505f14e105c93d7639e5c00`: transition engine capture-timeline aware;
- `edb74d6c9ba5db0ef8f4d43373c4961a14acd201`: observations manifest-aware;
- `7e56c657d1fcb758fae8ceace8e40b2996d8b8b7`: zero-candidate gap / reappearance regressions;
- `5414d499d2b30848d40d7fe9e141e11b7a1ec908`: transition report manifest-authoritative;
- `b94ac7044d5a07fb39c2781961bdaacae9d212d6`: prospective observation report;
- `0682130deed92a3f35d2d74b1ec0f4214420c30f`: zero-candidate baseline enrollment fix;
- `ab5f1d9b94d1be7a692d064c76175bba64cb4aad`: manifest/journal candidate-count cross-check.

Synthetic assistant-side scenario verified:
legacy T0 -> T1 prospective-new -> T2 full capture with zero candidates -> T3 scanner reappearance / Type-I observation, with cohort identity preserved and no invalidation inference.


## M4 Phase 2.5 / atomic capture transactions

Problem found during self-review:
journal append followed by manifest append is not a true cross-file atomic commit. Process interruption could leave a half-complete compatibility snapshot.

Implemented:
- `2e2750c82ef9d3b0c265de445fadd0c1bf13d5d2`: immutable atomic committed-capture transaction store;
- `4710545e7bb28405ba62565fc4423f6d4c713b46`: capture pipeline transaction-first;
- `dfd8560135c171ad901234d122d90d76737e660a`: reports consume committed transactions;
- `4f1bfa74feaa401447a4e95fe42dcc090bd88b4f`: freeze legacy baseline / capture-time-independent idempotency;
- `658e1b69133ead315e98fa66ea03eb424a39742b`: reports use frozen baseline + transactions, not live mirrors;
- `5b3395db3a3b0a4ebcc06c2bf20c39b864c27446`: transaction integrity/tamper hardening;
- `50e832f1a7f33fc3d57e74db4cd344f19bfc0d7a`: fix baseline JSON being scanned as transaction;
- `d1fee7d40efc2a7db32f6077585fd533c61f6d71`: monotonic transaction chronology after frozen baseline;
- `b803a2f723b2d6d3b97bd2f60fdc67cb44a1a1f7`: preserve legacy cutoff even when baseline candidate count is zero.

Assistant-side Python execution:
- transaction core syntax/execution: PASS;
- temp partial ignored: PASS;
- same facts/different capture time: PASS;
- frozen baseline idempotent/immutable: PASS;
- frozen T0 overwrite blocked: PASS;
- T1/T2 forward commits: PASS;
- historical backfill after newer transaction: PASS.

Hosted CI:
- run #914 completed failure with deterministic-tests steps=null/logs=null;
- same known runner-allocation failure, not code execution.


## M4 Phase 2.6 / mirror recovery and T0 closeout

Implementation:
- `5e8a2c8febc8b6e7caaf538906058cd5d0bb3a25`: mirror integrity / repair engine；
- `19f2b5b1e692627dc23d36a22d197d28171aeb59`: transaction IDs stamped into compatibility mirrors + auto repair；
- `d1fee7d40efc2a7db32f6077585fd533c61f6d71`: monotonic transaction chronology after frozen baseline；
- `b803a2f723b2d6d3b97bd2f60fdc67cb44a1a1f7`: zero-candidate legacy cutoff preservation。

Assistant-side executable verification:
- transaction core: PASS；
- same facts/different capture time idempotency: PASS；
- frozen baseline immutable: PASS；
- baseline-day overwrite blocked: PASS；
- T1/T2 forward chronology: PASS；
- historical backfill blocked: PASS；
- mirror corrupt/missing recovery: PASS；
- authoritative evidence unchanged by repair: PASS。

Actual uploaded T0 recomputed:
- 87 rows / 87 unique candidates；
- baseline audit 0 blockers / 6 warnings；
- transition baseline_only；
- 87 baseline_existing；
- 0 prospective_new；
- 0 prospective outcome eligible；
- prospective observation no_outcome_cohort / 0 rows。

Testing limitation:
assistant container lacks private-repo credentials; full repo pytest was not executed locally and is not claimed. GitHub hosted run #914 remains steps=null/logs=null runner-allocation anomaly.


## M4 Phase 2.7 / closed-day and suspension correctness

Static audit found and fixed multiple prospective-integrity edge cases:

- provider-confirmed closed day is now required before authoritative capture;
- local trade calendar must match provider target;
- partial-universe max_symbols runs are diagnostic-only;
- evidence-health returns structured blockers instead of crashing on corrupted authoritative evidence;
- empty frozen baseline marker is distinct from missing baseline;
- immutable transaction and legacy baseline validation are shared/fail-closed;
- D-027 adds confirmed full-day suspension carry-forward without fake bars.

Suspension semantics:
- only positive `trading_status=suspended` evidence qualifies;
- `intraday_suspended` does not;
- current-day bar + suspended event conflicts and fails;
- confirmed suspended stale analysis is carried to capture date with blocked execution and null OHLC;
- candidate remains present;
- first-seen suspended candidate cannot outcome-enroll;
- already enrolled candidate remains in cohort.

Key commits in this audit chain:
- `c78c1e8cf8c315ad4fbc69be21cf740db95b28d1`: provider-backed latest closed day;
- `5f9cbd35d8e96cb6785af5ac079a73cf0ea7fba2`: structured evidence-health blockers;
- `ce68a0a79c5da24d2ab87693f2e32ce6a8f78164`: shared immutable-evidence validation;
- `2a58676d8ac15df041655b8a41b5ddf42749e411`: suspension-aware journal schema;
- `b4349d9853ae25f5509c7149803c9168538e25ef`: suspension-aware capture pipeline;
- `07400d89d93a2c5385f6e88bddbc40d19cf9d152`: suspension facts in prospective observations;
- `690cf559446bc39dd5d0151e25da524d586483bf`: observation/report suspension regressions.


## M4 Phase 2.8 / methodology identity

Assistant-side source audit found that the first Phase 2.8 commit created a deterministic
methodology fingerprint module but did not yet bind that identity into authoritative evidence.

Closed in this batch:

- expanded methodology fingerprint coverage to include advanced RSI BAMM / indicator /
  lifecycle / 5-0 source files that can affect harmonic interpretation;
- capture transaction schema advanced to v2;
- new committed captures require `methodology_contract_version` and
  `methodology_fingerprint`;
- methodology identity is included in deterministic transaction-id material;
- active committed chain rejects methodology drift before append;
- schema-v1 pre-fingerprint captures remain readable only for explicit migration audit;
- evidence-health compares the current methodology fingerprint with the authoritative chain
  and blocks mismatch;
- snapshot compatibility manifest exposes methodology identity;
- mirror integrity now detects methodology-field drift;
- transition and prospective-observation reports expose the authoritative fingerprint;
- D-028 and `specs/m4-phase-2-8-methodology-identity.md` freeze the contract.

Additional correction from this audit:
the initial fingerprint list omitted `rsi_bamm.py`, `rsi_bamm_lifecycle.py`,
`five_zero_source.py`, `indicators.py` and `lifecycle.py`; they are now included and
protected by a regression test.

GitHub Actions remains infrastructure-limited:
latest push / pull_request deterministic-tests jobs completed with `steps=null`, so no pytest
or Web build actually executed. This is the same known runner-allocation anomaly and is not
counted as test pass or code failure.
