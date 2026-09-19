# M5 Phase 22 — Formal Main Release Integrity v1

状态：**Frozen / PR→main hosted release gates green; push-main observation pending merge**

## 1. 背景

Phase20 已通过 preserve-ancestry merge commit 把完整 M2→M3→M4→M5 lineage 合入正式 `main`。

Phase21 又建立了 current-main + private-M1 + latest Phase19 delivery 的真实收盘验收机制。

但合并后审计发现一个新的 CI 治理缺口：

- 通用 deterministic job 会在所有 push / PR 上跑 Python + Web build；
- 24 个 browser acceptance、Phase18、Phase21 主要通过 `m5/* / m3/* / m2/*` branch predicate 触发；
- Phase21 的 M4 methodology / Outcome Engine freeze guard 只在 `m5/main-real-closeout*` 上运行；
- 因此真正进入 `main` 后，并不存在一条长期、独立、明确的 full-history formal release gate。

这意味着 feature branch 的验收可能比正式 main 更严格。

Phase22 专门关闭这个结构性缺口。

## 2. 目标

新增独立 CI job：

`main-release-integrity`

显示名称：

`formal-main-release-integrity`

只在以下情况运行：

1. push 到 `main`；
2. pull request 的 target/base = `main`。

它是 additive gate：

- 必须等待 `deterministic-tests` 成功；
- 不替代 Python full regression；
- 不替代 Web build；
- 不修改已有 M2/M3/M5 feature-branch gates。

## 3. Full-history release checkout

正式 main release gate 必须：

- checkout exact PR head 或 push SHA；
- `fetch-depth: 0`；
- 不依赖 shallow history；
- 不读取 synthetic merge result 作为 provenance authority。

原因：

M4 methodology / Outcome Engine 与 Phase20/21 provenance 都依赖真实 Git ancestry。

## 4. Repository lineage integrity

新增：

`src/htcn/app/main_release_integrity.py`

`scripts/m5_main_release_integrity.py`

输出：

`artifacts/reports/m5-main-release-integrity.json`

每个正式 main release candidate 必须保留以下真实祖先：

- M2.31 source fidelity:
  `fbf964fb2230df2dd21138d2d99f037d3b5a382f`
- M3 merge:
  `edec5e21fb9e873daf8fb77fceaa0d89dbbd5b25`
- M4 methodology freeze:
  `c774c54928c33361952bf1a612a8555633449625`
- M4 Outcome Engine anchor:
  `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`
- M5 Phase20 main merge:
  `7ed0c56c2fe631f687a16cb8d4922030a21bc80a`
- M5 Phase21 main merge:
  `d8687f2bcc8d4a9d9b37eeac1430f6f88ff563d3`

任一不是 release HEAD 的 ancestor：

`blocked`

同时要求 tracked worktree clean。

该报告只负责 repository-lineage integrity。

它不替代浏览器或 M4 freeze steps。

## 5. Browser release gates

正式 main release job 必须重新执行既有 24 个 browser acceptance：

- smoke；
- lifecycle；
- execution-context；
- market / sector / concept context；
- context integrity；
- decision narrative / selection；
- operator queue / delta / index / history；
- daily review digest；
- review follow-up journal。

不能因为这些测试曾在 feature branch 上绿过，就在 main release 上跳过。

## 6. Phase18 release gate

正式 main release 必须：

1. build formal Phase18 deterministic fixture；
2. run Phase18 Chromium；
3. verify Phase18 screenshot/hash evidence。

必须继续覆盖：

- complete XABCD；
- forming XABCD；
- AB=CD；
- Shark 0XABC；
- FIVE_ZERO；
- Raw PRZ / Ideal Core / Envelope；
- prohibited future geometry；
- Shark no-D；
- 5-0 execution-refinement boundary。

## 7. Phase21 release gate

正式 main release 必须：

1. prepare Phase21 audit source from formal deterministic fixture；
2. run dynamic Phase21 Chromium；
3. independently verify Phase21 evidence。

因此任何 main push / PR→main 都再次证明：

- dynamic candidate enumeration；
- topology/node/leg equality；
- missing future node prohibition；
- Shark no-D；
- PRZ component semantics；
- explicit error visibility；
- page/console error=0；
- fetch/XHR=0；
- screenshot size/hash integrity。

这仍然只是 hosted acceptance mechanism，不冒充 private-M1 current-market closeout。

## 8. M4 frozen research guards

每个 formal main release candidate 必须执行：

`python scripts/m4_methodology_freeze_guard.py`

以及：

`python scripts/m4_outcome_engine_freeze_guard.py`

由于 release job 是 full-history checkout，不允许再次出现 Phase21 中的 shallow-history false blocker。

要求：

- methodology changed components = 0 / 37；
- Outcome Engine changed components = 0 / 4。

任何真实 drift：

release blocked。

## 9. Evidence artifact

main release job 无论成功失败都上传：

`htcn-main-release-integrity-<github.sha>`

包括：

- `m5-main-release-integrity.json`；
- browser screenshots；
- Phase18/21 browser evidence / verification reports。

retention:

30 days。

## 10. Workflow self-regression

新增 Python regression：

`tests/app/test_main_release_integrity.py`

不仅验证 lineage evaluator，还直接读取：

`.github/workflows/ci.yml`

冻结以下 workflow facts：

- `main-release-integrity` job 存在；
- display name 固定；
- trigger predicate 包含 push main / PR base main；
- `needs: deterministic-tests`；
- `fetch-depth: 0`；
- main release lineage script；
- 24-browser command；
- Phase18 build/test/verifier；
- Phase21 prepare/test/verifier；
- M4 methodology guard；
- Outcome Engine guard；
- release evidence artifact path。

因此未来有人误删 main release gate，会先在 Python regression 阶段失败。

## 11. 不做的事

Phase22 不：

- 改 harmonic identity；
- 改 Carney ratio；
- 改 Source Raw PRZ；
- 改 Source lifecycle；
- 改 Phase19 delivery；
- 改 Phase21 real-M1 semantics；
- 写 M4 evidence；
- 运行 private-M1；
- 计算 win rate / alpha / P&L；
- 执行交易。

## 12. Private-M1 boundary

Phase22 与 Phase21 的职责不同：

### Phase22

证明正式 `main` 的：

- code regression；
- browser semantics；
- provenance ancestry；
- M4 frozen research integrity。

### Phase21 local closeout

证明某一天真实 private-M1 产生的：

- Phase9 daily product；
- Phase19 exact latest delivery；
- real delivered HTML；
- current-market `full_closeout_ready`。

Phase22 不能替代后者。

## 13. Acceptance

- [x] dedicated main-release-integrity job exists；
- [ ] push main triggers formal release job；
- [x] PR targeting main triggers formal release job；
- [x] deterministic-tests is prerequisite；
- [x] full-history checkout；
- [x] lineage report ready；
- [x] M2.31 ancestor preserved；
- [x] M3 ancestor preserved；
- [x] M4 methodology ancestor preserved；
- [x] Outcome Engine ancestor preserved；
- [x] Phase20 merge ancestor preserved；
- [x] Phase21 merge ancestor preserved；
- [x] tracked worktree clean；
- [x] Web build in release job；
- [x] existing 24 Playwright green；
- [x] Phase18 Playwright/evidence green；
- [x] Phase21 Playwright/evidence green；
- [x] M4 methodology drift 0/37；
- [x] Outcome Engine drift 0/4；
- [x] evidence artifact uploaded；
- [x] workflow self-regression green；
- [ ] full Python regression green。

## 14. Branch-protection note

Repository workflow can guarantee that the formal main-release job exists and runs for PR→main / push main.

Whether GitHub server-side branch protection marks this job as a **required status check before merge** is a repository administration setting outside the repository file itself.

Phase22 therefore treats:

- workflow enforcement = repository code responsibility；
- server-side required-check policy = GitHub repository administration responsibility。

The codebase must not falsely claim branch protection is configured unless GitHub confirms it.


## 15. Hosted PR→main validation — 2026-09-19

Implementation checkpoint:

`a3ee750a0bb069caf68fddb84b7e6ad74de735f1`

Carrier PR:

- #34;
- head = `m5/main-release-integrity-v1`;
- base = `main`;
- base main SHA = `d8687f2bcc8d4a9d9b37eeac1430f6f88ff563d3`.

Actions:

**#1942 / 35429893144**

Results:

### prerequisite deterministic-tests

- status: success;
- Python: **832 passed**, 1163 warnings;
- Web build: success;
- existing Playwright: **24 passed**;
- Phase18 Playwright: **1 passed**;
- Phase18 evidence: valid, 10 checks / 5 screenshots;
- Phase21 dynamic Playwright: **1 passed**;
- Phase21 evidence: valid, 5 screenshots;
- deterministic browser artifact ID: **10580576017**.

### formal-main-release-integrity

- status: success;
- full-history checkout: success;
- release-lineage report: `status=ready`;
- M2.31/M3/M4/Phase20/Phase21 required ancestry: preserved;
- tracked worktree: clean;
- Web build: success;
- existing Playwright: **24 passed**;
- Phase18 Playwright/evidence: green;
- Phase21 Playwright/evidence: green;
- M4 methodology: **0 / 37 changed**, error_count=0;
- M4 Outcome Engine: **0 / 4 changed**, error_count=0;
- release evidence artifact ID: **10580297443**.

This proves the **PR targeting main** path is operational, not merely syntactically present.

## 16. Server-side branch protection read result

The connected GitHub integration attempted to read:

`/repos/shazhuya/HT-CN/branches/main/protection`

GitHub returned:

`403 Resource not accessible by integration`

Therefore Phase22 records only:

- repository workflow enforcement is verified;
- server-side “required status check” policy is **not observable through the current integration**;
- no claim is made that GitHub branch protection currently requires `formal-main-release-integrity` before merge.

This is not a code blocker.

## 17. Remaining post-merge observation

One acceptance item intentionally remains open before merge:

- actual **push-to-main** execution of `formal-main-release-integrity`.

The workflow predicate and self-regression already freeze that path, but Phase22 will observe the real push-main run created by the Phase22 merge before declaring the phase operationally complete.
