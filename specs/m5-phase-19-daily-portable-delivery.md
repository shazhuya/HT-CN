# M5 Phase 19 — Daily Portable Delivery Bundle / One-Click Closeout v1

状态：**Frozen / hosted CI green**

## 1. 目标

Phase18 已把 Portable Visual Workspace 的渲染语义推进到真实 Chromium + screenshot evidence。

当前真正影响日常使用的缺口变成：

> 每日收盘后，Phase9 产品结果、Phase14 v3、Phase16 v4、Phase17 Inspector/HTML 仍是分开的入口和分开的文件。

Phase19 把它们串成一个**生产侧便携交付链**，最终给用户一个可以直接保存、传输、解压打开的单文件 ZIP，同时保留不可变 archive。

## 2. 不修改被冻结的阶段

Phase19 不修改：

- Phase9 daily-close semantics；
- Phase14 handoff v3 schema/runner semantics；
- Phase16 handoff v4 schema/verifier；
- Phase17 Visual Semantics v2；
- Phase18 browser fixture/evidence semantics；
- M4 methodology / Outcome Engine。

Phase19 只做 orchestration + outer delivery packaging。

## 3. 生产链

正式顺序：

```
Phase9 daily-close report
  -> staged Phase14 v3
  -> current input identity
  -> staged Phase16 v4
  -> staged Phase17 inspector JSON + HTML
  -> outer portable delivery ZIP
  -> verify outer ZIP
  -> verify pipeline report remained unchanged
  -> immutable archive publish
  -> Phase19 latest aliases
  -> latest pointer LAST
```

latest pointer 最后写，作为 Phase19 最新成功交付的权威指针。

## 4. 外层 Portable Delivery Bundle v1

输出：

`artifacts/reports/htcn-daily-portable-delivery-v1.zip`

内部固定：

```
daily-portable-delivery-manifest.json
base/
  htcn-daily-handoff-v4.zip
workspace/
  m5-handoff-v4-inspector.json
  m5-handoff-v4-pattern-workspace.html
```

因为 v4 已原样嵌套 v3，所以外层无需再次重复 standalone v3。

## 5. Outer manifest binding

必须绑定：

- trade_date；
- current input identity fingerprint；
- Phase9 pipeline report SHA-256；
- nested v4 SHA-256；
- nested v4 status；
- visual semantics version=2；
- detail/error display-key count；
- 每个 member 的 size + SHA-256；
- Phase19 boundary contract。

## 6. Outer verifier

`verify_daily_portable_delivery_bundle()` 必须独立验证：

- safe ZIP member names；
- no duplicate members；
- exact manifest/member set；
- every member size/hash；
- nested v4 hash；
- nested v4 verifier = valid；
- trade date / input identity / counts / nested status 与 v4 一致；
- Inspector schema=2；
- Inspector source verification=valid；
- Inspector transport fingerprint 与 v4 一致；
- Visual Semantics version=2；
- Inspector boundary flags；
- HTML 包含正式 Visual Semantics v2 markers；
- HTML 无 `fetch(`；
- HTML 无 review write surface；
- outer status 与 nested v4 detail error count 一致。

## 7. Detail degraded 不是 transport failure

如果 v4 本身有效，但部分 current Queue key 得到 explicit detail error：

outer status：

`detail_degraded_portable_delivery`

允许 exit=0。

理由：

Phase16 已冻结：

每个 Queue key 必须是 exact detail 或 explicit error。

因此显式降级是合法可解释 transport，而不是 silent corruption。

## 8. Staging / failure safety

Phase19 所有 v3/v4/Inspector/HTML/outer ZIP 先在临时目录生成。

只有全部验证通过，并且 Phase9 pipeline report 在整个交付过程中 SHA-256 不变，才允许 promotion。

失败时：

- run report 更新；
- 上一份 latest pointer 不动；
- 上一份 immutable delivery archive 不动；
- Phase14/16 冻结别名不动。

## 9. Immutable archive

每次成功交付存入：

`artifacts/deliveries/m5/<trade_date>/<bundle_sha_prefix>/`

包含：

- portable delivery ZIP；
- direct v4 ZIP；
- inspector JSON；
- workspace HTML；
- archive manifest。

目录先写到同交易日的 hidden temp directory，再原子 rename 到最终 hash-addressed directory。

## 10. Phase19-specific latest aliases

成功后更新：

- `artifacts/reports/htcn-daily-portable-delivery-v1.zip`
- `artifacts/reports/m5-daily-portable-v4.zip`
- `artifacts/reports/m5-daily-portable-inspector.json`
- `artifacts/reports/m5-daily-portable-workspace.html`

这些是 Phase19 自己的 convenience aliases。

明确不覆盖：

- Phase14 `htcn-daily-handoff-v3.zip`
- Phase16 `htcn-daily-handoff-v4.zip`
- Phase16 `m5-handoff-v4-*.json/html`

## 11. Latest pointer vs run report

每次运行都写：

`m5-daily-portable-delivery-run.json`

它记录本次成功/失败。

只有完整成功才更新：

`m5-daily-portable-delivery-latest.json`

因此一次失败不能让“最新成功交付”被错误指向失败产物。

## 12. One-click

新增：

`scripts/m5_build_daily_portable_delivery.py`

以及：

`运行HT-CN每日收盘并生成便携复盘包.bat`

BAT 一次执行：

1. Phase9 daily close；
2. 若产品 lane 成功，执行 Phase19 delivery；
3. 输出最终 ZIP/HTML/latest pointer。

M4 research degraded 仍遵守 Phase9 既有规则，不阻塞 M5 product-ready 交付。

## 13. Boundary contract

固定：

- nested_v4_unmodified=true；
- latest_pointer_is_authoritative_for_phase19=true；
- frozen_phase14_16_aliases_overwritten=false；
- authoritative_evidence=false；
- writes_m4_evidence=false；
- imports_product_state=false；
- writes Queue/history/review=false；
- creates_review_events=false；
- mutates harmonic identity / Raw PRZ / lifecycle=false；
- no score / outcome ranking / alpha；
- is_trade_instruction=false。

## 14. Browser boundary

Phase19 生产链生成真实当日 HTML，但**不在生产 runner 内启动 Playwright**。

Phase18 已负责 renderer semantics 的 hosted browser QA。

未来如果需要对某次真实市场 delivery 做浏览器截图审计，应建立独立 real-artifact QA gate，而不是把 Chromium 依赖塞进每日产品生成主链。

## 15. Acceptance

- [x] Phase9 product not ready -> fail before v3；
- [x] v3 failure -> no v4/workspace/outer promotion；
- [x] input identity invalid/mismatch -> fail closed；
- [x] v4 failure -> previous latest pointer preserved；
- [x] workspace failure -> previous latest pointer preserved；
- [x] pipeline report changes during delivery -> no promotion；
- [x] outer bundle verifier validates nested v4；
- [x] outer bundle validates Inspector identity/date/version；
- [x] outer bundle validates HTML offline boundary；
- [x] valid detail-degraded v4 -> valid degraded outer bundle；
- [x] success publishes immutable hash-addressed archive；
- [x] success updates Phase19 aliases；
- [x] latest pointer written last；
- [x] frozen Phase14/16 aliases untouched；
- [x] one-click daily-close + delivery entry；
- [x] Python regression green；
- [x] Web build green；
- [x] existing browser gates green；
- [x] Phase18 browser gate remains green；
- [x] v4 transport/verifier drift=0；
- [x] M4 methodology drift=0；
- [x] Outcome Engine drift=0。


## 16. Hosted validation closeout — 2026-09-19

Validated implementation checkpoint:

`e8d46855f775f57bf7e413575c82806b74b24aba`

Hosted CI:

- Actions **#1876 / 35426314518**: success;
- Python: **801 passed**, 1163 warnings;
- Web build: success;
- existing deterministic Playwright: **24 passed**;
- Phase18 portable visual Playwright: **1 passed**;
- Phase18 semantic checks: **10 / 10**;
- Phase18 screenshots: **5 / 5**;
- Phase18 evidence verifier: valid;
- browser evidence artifact upload: success;
- artifact ID: **10579530605**.

Diff audit against Phase18:

- branch is ahead-only;
- Phase19 implementation adds five files only;
- existing Phase18 implementation files changed: 0;
- handoff v4 transport/verifier drift: 0;
- Visual Semantics v2 drift: 0;
- M4 methodology drift: 0;
- Outcome Engine drift: 0.

Interpretation:

**Phase19 daily portable delivery v1 is code-complete and hosted-CI-green.**

The hosted validation proves orchestration/failure-safety semantics with deterministic fakes. It does not claim that GitHub CI generated a real current-market portable delivery from the user's local market database.
