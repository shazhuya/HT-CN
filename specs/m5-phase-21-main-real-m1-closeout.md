# M5 Phase 21 — Main Real-M1 Closeout / Current Delivery Acceptance v1

状态：**Frozen / hosted acceptance mechanism CI green**

## 1. 目标

Phase20 已将完整 M2→M3→M4→M5 ancestry 通过 merge commit 正式整合进 `main`。

Phase19 已能在有真实 M1 数据的机器上生成 staged/verified：

`daily close -> v3 -> v4 -> Visual Semantics v2 -> portable delivery`

Phase21 不再增加新的谐波算法、transport 或产品工作流。

它只解决最后一个验收缺口：

> **当前 main HEAD + 私有真实 M1 + 当天 Phase19 latest delivery 是否彼此严格绑定，并且这个真正的当天 HTML 是否在 Chromium 中按其自身 transported visual semantics 正确渲染。**

Hosted CI 只能验证 Phase21 验收机制本身，不能冒充真实 A 股当天 closeout。

## 2. 两层验收

Phase21 分为两个独立 gate：

1. **structural closeout**
2. **real browser closeout**

最终 READY 必须两者都通过，并绑定同一：

- trade_date；
- Phase19 bundle SHA-256。

## 3. Structural closeout

模块：

`src/htcn/app/main_real_closeout.py`

入口：

`scripts/m5_main_real_closeout.py`

报告：

`artifacts/reports/m5-main-real-closeout.json`

### 3.1 Git / main binding

真实 closeout 必须：

- current branch = `main`；
- current HEAD 为 40-char SHA；
- worktree clean；
- Phase9 pipeline preflight branch = `main`；
- Phase9 pipeline preflight HEAD = 当前 main HEAD；
- Phase9 pipeline preflight clean=true。

因此旧 commit 生成的 pipeline/delivery 不能在新 main HEAD 上被重新包装成“当前验收通过”。

### 3.2 Phase9 product gate

必须：

`m5_product_ready=true`

以下状态不阻断 Phase21 product closeout，但必须成为 warning：

- context refresh degraded；
- Operator history degraded；
- review digest degraded；
- M4 research degraded。

这些 warning 不能被静默隐藏。

### 3.3 Phase19 latest-run anti-stale gate

Phase19 `run report` 必须是本次成功状态：

- exit_code=0；
- status = complete_portable_delivery 或 detail_degraded_portable_delivery；
- pipeline_report_unchanged=true。

理由：

Phase19 失败时会故意保留上一份 successful latest pointer。

因此 Phase21 必须同时看 **latest run + latest pointer**，否则昨天的成功 pointer 可能冒充今天成功。

### 3.4 Latest pointer / current pipeline binding

`m5-daily-portable-delivery-latest.json` 必须：

- schema=1；
- trade_date 有效；
- bundle SHA-256 有效；
- input identity fingerprint 有效；
- pipeline report SHA-256 = 当前 pipeline report 实际 SHA-256。

### 3.5 Portable bundle gate

Latest pointer 的 portable delivery：

- 文件实际存在；
- 文件 SHA-256 = pointer bundle SHA-256；
- `verify_daily_portable_delivery_bundle()` = valid；
- bundle trade_date = pointer；
- bundle input identity = pointer；
- bundle pipeline hash = pointer。

### 3.6 Immutable archive / convenience alias gate

Immutable archive manifest 必须和 pointer 一致：

- trade date；
- bundle SHA；
- input identity；
- pipeline hash。

Archive 中四个成员：

- portable delivery；
- handoff v4；
- inspector JSON；
- workspace HTML；

必须：

- 实际文件 hash = archive manifest；
- Phase19 convenience alias hash = 同一个 immutable archive hash。

任何 alias drift/tamper 都是 blocker。

## 4. Explicit degradation semantics

以下属于 warning，不自动变成 blocker：

### context / M4 degradation

沿用 Phase9 product/research 分离。

### explicit Phase16 detail error

如果 Phase16 已满足 exhaustive：

`detail_keys ∪ error_keys == Queue keys`

则：

`detail_degraded_portable_delivery`

仍可进入真实 browser audit。

Browser 必须把 explicit error 项真实展示出来。

**silent omission 永远不允许。**

## 5. Real browser source

模块：

`src/htcn/app/main_real_browser_audit.py`

准备入口：

`scripts/m5_prepare_main_real_browser_audit.py`

正常真实模式读取：

- `m5-main-real-closeout.json`
- `m5-daily-portable-delivery-latest.json`
- pointer 指向的真实 workspace HTML；
- pointer 指向的真实 Inspector JSON。

然后把 HTML 原字节复制为：

`apps/web/public/latest-real-portable-workspace.html`

同时写：

`artifacts/reports/playwright/phase21-real-delivery-browser-source.json`

Source report 绑定：

- mode=phase19_latest；
- trade_date；
- Phase19 bundle SHA；
- workspace hash；
- inspector hash；
- candidate count；
- detail available/error count；
- schema counts；
- structural closeout status/hash。

Browser source 不读取行情库，不重新分析 pattern。

## 6. Dynamic real-browser audit

Playwright：

`apps/web/tests/main-real-portable-delivery.spec.ts`

它**不写死股票、候选数量或 schema 组合**。

它直接解析 HTML 内嵌：

`#htcn-data`

然后逐个 `portable_items` 审计。

### 每个 exact detail

必须：

- topology status 为 complete / forming_prefix；
- SVG `data-node-label` 精确等于 `observed_labels`；
- SVG `data-leg-name` 精确等于 transported visual semantics legs；
- `missing_future_labels` 不得出现在实际 SVG；
- Shark / 0XABC 不得出现 D；
- PRZ component names 精确匹配；
- PRZ component semantic roles 精确匹配；
- source_prz_available=true 时 Source Raw PRZ layer 必须存在。

### explicit detail error

必须：

- UI 明确展示 error；
- error count 与 Inspector/source report 一致。

### Schema coverage

Browser audit 自动统计当日实际存在的 schema。

每一种当日实际 schema 至少截一张图。

因此：

- 当天没有 Shark，不会伪造 Shark 测试；
- 当天有 Shark，就必须按真实 transported 0XABC semantics 验收。

## 7. Future-point invariant

Browser audit 计算：

`future_point_violation_count`

必须为：

`0`

形成中缺失节点不能被实际 SVG 渲染。

## 8. Layer-toggle check

如果真实当天至少有一个候选同时包含：

- Source Raw PRZ；
- Component Envelope；

则 Chromium 实际执行：

1. Source Raw PRZ 默认存在；
2. Envelope 默认不存在；
3. 打开 Envelope -> 出现；
4. 关闭 Source Raw PRZ -> 消失；
5. 重新打开 -> 出现；
6. 关闭 Envelope -> 消失。

若当天没有任何满足该条件的真实候选，则不伪造候选；该天只记录无可执行 toggle sample，不应成为谐波语义失败。

## 9. Browser runtime safety

真实 browser audit 必须：

- page errors = 0；
- console errors = 0；
- XHR/fetch = 0。

Portable workspace 仍然是 offline read-only artifact。

## 10. Screenshot evidence

输出：

- overview screenshot；
- 每个当天实际 schema 至少一张 screenshot。

Evidence：

`artifacts/reports/playwright/phase21-real-delivery-browser-evidence.json`

记录：

- trade date；
- source bundle SHA；
- candidate/detail/error counts；
- schema counts；
- audited detail count；
- explicit errors；
- future-point violations；
- page/console errors；
- no-network flag；
- screenshot path/size/SHA；
- frozen boundary flags。

## 11. Independent evidence verification

入口：

`scripts/m5_verify_main_real_browser_evidence.py`

独立验证：

- source/evidence identity；
- trade date；
- candidate/detail/error counts；
- schema counts；
- exhaustive audited detail count；
- future violation=0；
- page/console errors=0；
- no fetch/XHR；
- semantic flags；
- screenshot exists / >10KB / size/hash；
- non-mutation boundaries。

输出：

`phase21-real-delivery-browser-verification.json`

## 12. Final closeout

入口：

`scripts/m5_finalize_main_real_closeout.py`

输出：

`artifacts/reports/m5-main-real-closeout-final.json`

最终 READY 要求：

- structural status = ready / ready_with_warnings；
- browser verification = valid；
- structural trade date = browser trade date；
- structural bundle SHA = browser source identity。

最终状态：

- `ready`
- `ready_with_warnings`
- `invalid`

`full_closeout_ready=true` 只在没有 hard blocker 时成立。

## 13. Zero-candidate day

零候选日是合法情况，只要：

- Phase9/Phase19 structural chain 完整；
- bundle/identity/archive/pointer 全部有效；
- browser HTML 能正常打开；
- candidate_count=0；
- detail/error count=0；
- overview screenshot 存在；
- page/console/network errors=0。

不得为了“有图可验”制造虚假候选。

## 14. Hosted CI fixture boundary

GitHub-hosted CI 没有用户私有 M1。

因此 CI 只验证 Phase21 **验收机制**：

1. 先生成正式 Phase18 deterministic fixture；
2. `m5_prepare_main_real_browser_audit.py --fixture`；
3. 运行 Phase21 dynamic Playwright；
4. 独立验证 Phase21 browser evidence；
5. 上传 browser evidence。

CI 成功只能写：

> Phase21 acceptance mechanism is hosted-CI-green.

不能写：

> real current-market closeout passed.

## 15. One-click real local closeout

新增：

`运行HT-CN主线真实A股最终验收.bat`

正式使用前提：

- Phase21 已合入 main；
- 用户本地 checkout 在 main；
- worktree clean；
- .venv / web dependencies / Playwright Chromium 已准备好。

流程：

1. 运行 Phase19 的“每日收盘 + 便携交付”；
2. structural closeout；
3. prepare real browser source；
4. Chromium audit；
5. independent browser evidence verification；
6. final closeout。

Phase21 不自动安装 Playwright 或 npm dependencies；缺依赖时明确失败，不把网络安装混进真实验收语义。

## 16. Authority boundary

Phase21：

- 不改变 harmonic identity；
- 不改变 Source Raw PRZ；
- 不改变 Source lifecycle；
- 不写 Queue/history/review；
- 不写 M4 evidence；
- 不产生 reviewed/follow_up；
- 不计算 win rate；
- 不计算 alpha；
- 不做 outcome ranking；
- 不执行交易。

Browser evidence 是产品 QA，不是 M4 authoritative evidence。

## 17. Acceptance

- [x] structural verifier current-main binding；
- [x] pipeline-head mismatch fail closed；
- [x] latest-run anti-stale gate；
- [x] pointer/current pipeline hash binding；
- [x] portable bundle verification；
- [x] immutable archive verification；
- [x] latest alias hash verification；
- [x] explicit context/M4/detail degradation -> warning；
- [x] latest real workspace browser-source binding；
- [x] dynamic all-candidate Chromium audit；
- [x] missing future nodes never render；
- [x] Shark never gets D；
- [x] explicit detail errors render；
- [x] schema counts exhaustive；
- [x] page/console errors=0；
- [x] no XHR/fetch；
- [x] screenshots hash/size verified；
- [x] final structural/browser identity binding；
- [x] zero-candidate day supported；
- [x] Python full regression green；
- [x] Web build green；
- [x] existing Playwright green；
- [x] Phase18 browser/evidence green；
- [x] Phase21 hosted fixture browser/evidence green；
- [x] M4 methodology drift=0；
- [x] Outcome Engine drift=0。

## 18. Real-market completion boundary

Phase21 code/CI 可以由 GitHub hosted 环境完整验收。

但 **real current-market `full_closeout_ready`** 只能由持有当前私有 M1 数据的真实机器生成。

该本地动作应只在 Phase21 合入 main 后做一次，不用于替代 assistant/cloud routine testing。


## 19. Hosted validation closeout — 2026-09-19

Validated implementation checkpoint:

`576f8aa4e950b9b416da27c69933dae75004903d`

Hosted CI:

- Actions **#1927 / 35428668864**: success;
- Python **824 passed**, 1163 warnings;
- Web build: success;
- existing Playwright: **24 passed**;
- Phase18 browser acceptance: **1 passed**;
- Phase18 evidence verifier: valid, 10 semantic checks / 5 screenshots;
- Phase21 dynamic browser audit: **1 passed**;
- Phase21 browser evidence verifier: valid;
- deterministic fixture candidate count: 5;
- fixture schema counts: XABCD 2 / ABCD 1 / 0XABC 1 / FIVE_ZERO 1;
- Phase21 screenshot count: 5;
- M4 methodology freeze: **0 / 37 changed**, error_count=0;
- M4 Outcome Engine freeze: **0 / 4 changed**, error_count=0;
- browser evidence artifact upload: success.

Development blockers found and fixed without weakening acceptance:

1. successful integer zero values were initially collapsed by Python `value or -1` patterns in new Phase21 verifiers;
2. a broad Playwright `Visual Semantics v2` locator matched both subtitle and footer;
3. methodology ancestry guard initially ran on shallow Git history; Phase21 now fetches full ancestry before both M4 freeze guards.

All original semantic assertions remain.

Important boundary:

**Hosted CI proves that the Phase21 acceptance mechanism is green. It does not prove that the user's current private-M1 real-market closeout has run.**

The latter requires the one-click command on a clean, current `main` checkout after this phase is merged.
