# M5 Phase 23 — Real-M1 Final Closeout Preflight / Single-Action Safety v1

状态：**Frozen / operationally closed on main; real private-M1 run remains pending by design**

## 1. 目标

Phase21 已建立真实 private-M1 最终验收链：

- 当前 clean main；
- Phase9 daily close；
- Phase19 portable delivery；
- exact latest structural binding；
- dynamic Chromium；
- screenshot/hash evidence；
- final `full_closeout_ready`。

Phase22 又把正式 main 的发布门禁补成 full-history release gate。

但现有 `运行HT-CN主线真实A股最终验收.bat` 仍存在一个实际操作风险：

> 它先进入 daily close / M1 更新，之后才可能发现本地 checkout 不是最新 main、Node/npm 缺失、Playwright Chromium 没装、catalog/Parquet 已损坏、磁盘不足等环境问题。

Phase23 的目标不是增加交易算法。

Phase23 只解决：

> **在任何真实 M1 / product / M4 状态发生变化之前，用一次只读 preflight 尽可能提前发现本地最终验收必然会失败的问题。**

用户仍只需要运行一个 BAT。

## 2. Single-action order

最终唯一推荐入口保持：

`运行HT-CN主线真实A股最终验收.bat`

Phase23 后固定顺序：

0. read-only Phase23 preflight；
1. Phase9 daily close + Phase19 verified portable delivery；
2. Phase21 structural binding；
3. prepare exact latest Phase19 workspace；
4. dynamic Chromium audit；
5. independent browser evidence verification；
6. final structural/browser identity-bound closeout；
7. complete。

Preflight 非零：

- 后续步骤全部不启动；
- M1 daily update 不启动；
- Phase19 不启动；
- M4 capture/outcome 不启动；
- 旧的 latest pointer 不被触碰。

## 3. Read-only / no-auto-repair contract

Phase23 preflight 明确禁止：

- `git pull`；
- `git fetch`；
- checkout / reset / merge；
- pip install；
- npm install / npm ci；
- Playwright install；
- M1 update；
- catalog schema initialization；
- product cache/history/review write；
- Phase19 delivery；
- M4 capture/outcome/evidence write。

允许的外部只读探测：

- `git ls-remote origin refs/heads/main`；
- provider trade-calendar liveness probe；
- Node/npm dependency inspection；
- ephemeral headless Chromium launch。

允许的本地输出只有：

`artifacts/reports/m5-real-closeout-preflight.json`

该文件是运行诊断，不是 M4 authoritative evidence。

## 4. Git / main freshness gate

Hard blockers：

- 当前目录不是 Git repo；
- current branch != `main`；
- worktree 非 clean；
- `origin/main` 无法通过 ls-remote 解析；
- local HEAD != exact remote main SHA；
- Phase22 main merge
  `56b6da0d30b951c3ff569ff4739ddbe6e5d3e695`
  不是当前 HEAD 的真实祖先。

不自动修复远端漂移。

若本地旧于 main：

preflight 只报告并退出。

## 5. Python environment gate

Hard blockers：

- Python 非 3.13；
- 当前 executable 不是项目 `.venv`；
- required imports 失败：
  - duckdb；
  - pandas；
  - pyarrow；
  - htcn。

Phase23 不安装缺失依赖。

## 6. M1 catalog read-only gate

Catalog：

`data/market/catalog.duckdb`

必须：

- 文件存在；
- 使用 DuckDB `read_only=True` 打开；
- required tables 存在：
  - security_master；
  - daily_dataset；
  - trade_calendar；
  - sync_task。

重要：

Phase23 不复用 `DataCatalog(...)` 作为 preflight opener，因为该 constructor 有 schema initialization 行为。

这保证 preflight 不会通过“检查”顺便写 DB。

## 7. Current initialized-universe semantics

Phase23 不偷偷改变当前产品范围。

Hard requirement：

- catalog 中存在至少一个 listed SSE/SZSE；
- 已初始化 SSE/SZSE dataset count > 0。

但：

`initialized_scope_count < listed_scope_count`

只产生 warning：

`m1_full_listed_coverage`

不 hard block。

原因：

当前 M5/M4 正式语义基于“已初始化数据集 universe”运行；此前真实 M4 也曾以 55 个 initialized instruments 工作。

把 5000+ 全市场初始化强行变成 Phase23 新要求会改变现有产品语义，因此禁止。

BSE 仍 deferred。

## 8. Base Parquet integrity

对每个已初始化 SSE/SZSE daily_dataset：

检查：

- parquet_path 非空；
- catalog row_count > 0；
- first/last trade date 存在且有序；
- 只对当前 listed SSE/SZSE 的 active initialized dataset 做 hard integrity gate；
- 已保留但当前 inactive/delisted 的历史 dataset 只计数，不阻塞，保持与 Phase9 daily pipeline 的 active-universe 选择一致；
- Parquet 文件存在且 size > 0；
- PyArrow metadata 可打开；
- required columns 存在：
  - instrument_id；
  - trade_date；
  - open/high/low/close；
  - volume；
- Parquet metadata row count > 0；
- base Parquet actual metadata row count == catalog row_count。

这些是 metadata/file-level checks。

Phase23 不把全历史加载成 pandas frame，因此不会重做完整 M1 health audit。

## 9. Daily delta integrity

目录：

`data/market/daily_delta`

如果存在已有 `*.parquet`：

每个文件必须：

- size > 0；
- PyArrow metadata 可打开；
- required daily columns 完整；
- rows > 0。

没有 delta 文件是合法状态。

损坏 delta 是 hard blocker，因为 `DailyHistoryView` 会消费它。

## 10. Trading calendar

`trade_calendar` 必须非空。

Preflight 记录：

- count；
- first；
- last。

Preflight 不要求本地 calendar 已经覆盖“今天”，因为 daily updater 自己负责确定 latest closed A-share session 并追加最新交易日。

## 11. Provider liveness

在任何 M1 update 之前运行隔离 subprocess：

- AkShare primary；
- Sina fallback；
- BaoStock fallback；
- 请求最近约 21 calendar days 的 trade calendar；
- 必须返回至少一个交易日。

Timeout / all-provider failure：

hard block。

这只是 liveness probe，不代表承诺完整 daily update 一定成功。

## 12. Node / npm / Playwright gate

Hard blockers：

- node 不存在；
- npm 不存在；
- npx 不存在；
- `npm ls --depth=0 --json` 失败；
- `@playwright/test` 无法 resolve；
- Playwright Chromium executable 不存在；
- ephemeral headless Chromium 无法真实 launch + close。

这里特意要求真实 Chromium launch，而不只检查文件路径。

Phase23 不自动安装 Chromium。

## 13. Local write-capability diagnostics

不通过创建测试文件来“验证写权限”。

只检查目标或最近 existing parent 的 write permission：

- `artifacts/reports`；
- `data/market/daily_delta`；
- `data/product/m5`。

因此 preflight 不留下 probe temp file。

Hard block：
不可写。

## 14. Disk space

Hard minimum：

1 GiB free。

Recommended：

5 GiB free。

- <1 GiB：block；
- 1–5 GiB：warning；
- >=5 GiB：pass。

推荐阈值是运行安全余量，不是市场/研究语义。

## 15. Report schema

输出：

`artifacts/reports/m5-real-closeout-preflight.json`

包含：

- schema version；
- status：
  - ready；
  - ready_with_warnings；
  - blocked；
- HEAD；
- exact contract flags；
- check_count / passed_count；
- blocker_count / warning_count；
- errors / warnings；
- per-check detail + structured data；
- next_action。

Blocked 时：

`next_action=stop_before_any_m1_or_product_mutation`

Ready / warning-only：

`next_action=daily_close_and_phase19_may_start`

## 16. Warning policy

Phase23 v1 只有两项 warning-only：

1. `m1_full_listed_coverage`
2. `free_disk_recommended`

其余环境、Git、M1 integrity、provider、Node、Chromium、hard disk minimum 都是 blocker。

禁止随意把 blocker 降级成 warning 来提高通过率。

## 17. Test contract

新增：

`tests/app/test_real_closeout_preflight.py`

覆盖：

- all-ready；
- blocker fail-closed；
- partial universe warning-only；
- disk min/recommended 分层；
- required-check set 守恒；
- no-auto-repair contract；
- critical check severity；
- BAT preflight-before-daily ordering；
- BAT/module forbidden install/update command；
- Phase21 structural/browser chain preserved；
- warning whitelist exact match；
- real temporary DuckDB + Parquet valid path；
- catalog row_count mismatch detection；
- corrupt daily-delta detection；
- inactive/delisted historical dataset remains nonblocking, matching Phase9 active scope。

## 18. Explicit non-goals

Phase23 不：

- 修改 harmonic identity；
- 修改 Carney ratios；
- 修改 Source Raw PRZ；
- 修改 Source lifecycle；
- 修改 Phase19 transport semantics；
- 修改 Phase21 browser semantics；
- 修改 M4 methodology/outcome engine；
- 运行真实 private M1 on hosted CI；
- 产生 win rate / alpha / P&L；
- 执行交易。

## 19. Acceptance

- [x] read-only preflight core；
- [x] CLI；
- [x] final BAT preflight-first；
- [x] no git pull/fetch；
- [x] no dependency install；
- [x] branch main gate；
- [x] remote main exact SHA gate；
- [x] Phase22 ancestor gate；
- [x] clean worktree gate；
- [x] Python 3.13 + project venv gate；
- [x] dependency import gate；
- [x] catalog read-only open；
- [x] required tables；
- [x] initialized SSE/SZSE scope；
- [x] partial full-market coverage warning-only；
- [x] base Parquet metadata integrity；
- [x] daily delta integrity；
- [x] calendar present；
- [x] provider liveness；
- [x] node/npm/npx；
- [x] npm dependency tree；
- [x] Playwright package；
- [x] Chromium executable；
- [x] real headless launch；
- [x] write-capability diagnostics；
- [x] disk hard/recommended thresholds；
- [x] report schema；
- [x] failure stops before daily close；
- [x] Phase21 chain still executed after preflight；
- [x] Python regressions green；
- [x] Web build green；
- [x] existing Playwright green；
- [x] Phase18 green；
- [x] Phase21 green；
- [x] formal-main-release-integrity green on PR→main；
- [x] M4 methodology drift 0/37；
- [x] Outcome Engine drift 0/4；
- [x] merge to main；
- [x] push-main formal release gate green。


## 20. Hosted implementation validation — 2026-09-19

Validated branch checkpoint:

`47c9e4f2d525632d37f6aec0cf2c83e7300e0760`

Carrier PR:

- #36；
- head = `m5/real-closeout-preflight-v1`；
- base = formal `main` at `a3f02615d47d91c60580a0feeedc0bdb3f4dd58d`。

Actions:

**#1973 / 35432978519**

### deterministic-tests

- status: success；
- Python: **847 passed**, 1163 warnings；
- Web build: success；
- existing Playwright: **24 passed**；
- Phase18 portable visual Playwright: **1 passed**；
- Phase18 evidence verifier: valid, 10 checks / 5 screenshots；
- Phase21 dynamic Playwright: **1 passed**；
- Phase21 evidence verifier: valid；
- browser artifact ID: **10581870545**。

### formal-main-release-integrity

- status: success；
- full-history release lineage: **ready**；
- formal release Web build: success；
- existing Playwright: **24 passed**；
- Phase18 Playwright/evidence: green；
- Phase21 dynamic Playwright/evidence: green；
- M4 methodology changed components: **0 / 37**；
- M4 Outcome Engine changed components: **0 / 4**；
- formal release artifact ID: **10582195249**。

Hosted CI proves the Phase23 code/contract and existing product/browser/research-freeze compatibility.

It does **not** run the private-M1 preflight against the user's local market database, because hosted CI does not possess that private M1 state.

## 21. Implementation correction made before freeze

Initial Phase23 draft treated every historical SSE/SZSE `daily_dataset` not currently listed as an orphan blocker.

That was too strict relative to the existing Phase9 daily pipeline, which selects active datasets by current `listed_ids`.

Before freeze Phase23 was corrected to:

- hard-check only currently listed SSE/SZSE active initialized datasets；
- retain `inactive_dataset_count` as diagnostic；
- do not require stale/delisted historical datasets to have active Parquet validity for current closeout；
- add a regression where an inactive/delisted retained dataset points to a missing historical file but the current active dataset remains valid and the probe still passes。

This correction avoids silently changing the current product universe contract.

## 22. Remaining acceptance after hosted implementation green

Integration is now complete.

- PR #36 merged to `main` using merge commit `c309f782bd31ccf3e963be3bb65670f6e3788174`；
- merge-generated push-main Actions #1982 / `35433384021` passed；
- `formal-main-release-integrity` passed on the merged main；
- final release artifact ID: `10581176575`。

The real current-market/private-M1 `full_closeout_ready` remains a separate Phase21 outcome produced only when the user later runs the one-click final BAT on the machine that owns the private M1 database. This is an empirical boundary, not unfinished Phase23 engineering.


## 23. Post-merge operational validation

Phase23 main merge commit:

`c309f782bd31ccf3e963be3bb65670f6e3788174`

Merge method:

- merge commit；
- no squash；
- no rebase。

Post-merge ancestry audit confirmed the following remain real ancestors of formal `main`:

- Phase23 final PR head `12529ae93206e9ca83af73c1bb721db78e1129eb`；
- Phase22 main merge `56b6da0d30b951c3ff569ff4739ddbe6e5d3e695`；
- Phase21 main merge `d8687f2bcc8d4a9d9b37eeac1430f6f88ff563d3`；
- Phase20 main merge `7ed0c56c2fe631f687a16cb8d4922030a21bc80a`；
- M4 methodology freeze `c774c54928c33361952bf1a612a8555633449625`；
- M4 Outcome Engine anchor `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`；
- M3 merge；
- M2.31 source-fidelity checkpoint。

The merge generated a real main push:

**Actions #1982 / 35433384021**

Observed results:

- event = `push`；
- head branch = `main`；
- head SHA = Phase23 merge commit；
- deterministic-tests = success；
- Python = **847 passed**, 1163 warnings；
- formal-main-release-integrity = success；
- release lineage = **ready**；
- formal release existing Playwright = **24 passed**；
- Phase18 Playwright = **1 passed**；
- Phase18 evidence = valid；
- Phase21 dynamic Playwright = **1 passed**；
- Phase21 evidence = valid；
- M4 methodology drift = **0 / 37**；
- M4 Outcome Engine drift = **0 / 4**；
- formal release artifact ID = **10581176575**。

Therefore Phase23 engineering/integration is operationally closed.

What remains intentionally unexecuted:

- the first real Phase23 preflight against the user's private local M1；
- the subsequent real current-market Phase21 `full_closeout_ready` result。

Those require the machine that actually owns private M1 and are not suitable for routine assistant-side testing.
