# M5 Phase 11 — Daily Operator History / Change Journal v1

status: frozen
validated_code_checkpoint: `504cc063d93e999dcbac1b131e14f475beacd4d0`
validated_ci_run_id: `35384764795`
validated_ci_run_number: `1699`
validation_pr: `#23` (draft CI carrier only)
date: `2026-09-19`

## 目标

把每天 **最终** M5 Operator snapshot 的产品级观察长期留档，并提供跨日变化查询。

这个 history 是产品 observability / review layer，不是 M4 prospective authoritative evidence，不拥有 lifecycle，不用于计算历史胜率、alpha、预测分数或交易排序。

## 写入时点

History 只能在 Phase 9 最终 non-force cache revalidation 成功后写入。

每日顺序继续是：

1. M1 fresh market data；
2. M3 context sync（best effort）；
3. M5 initial Operator cache；
4. independent M4 research lane；
5. M5 final cache revalidation；
6. **M5 Operator History append**。

因此 history 记录的是本次每日流水线的最终产品状态，而不是 initial cache 或研究侧可能改变 QFQ 前的中间状态。

History 写入/查询失败只令 `m5_history_ready=false`，不得把一个已经满足 Phase 9 条件的 `m5_product_ready=true` 改为 false，也不得改写 `m4_research_ready`。

## Source binding

每次 append 前必须重新验证最终：

- `artifacts/reports/m5-operator-snapshot.json` schema v2；
- `product_ready=true`；
- `observation_integrity=single_as_of`；
- product cache 为 persisted status；
- freshness=current；
- input identity stable；
- report as-of / expected trade date / queue trade date 一致；
- report input identity 与 cache input identity 一致；
- exact snapshot 被限制在 `data/product/m5/operator_queue/`；
- exact snapshot schema v1 / contract v2；
- snapshot trade date / input identity / queue 与 report 一致；
- snapshot 继续声明 non-authoritative / no M4 write。

## Observation identity

每一个 history observation 使用 SHA-256 identity，绑定：

- trade date；
- source snapshot generated-at；
- Operator Input Identity fingerprint；
- final M5 report SHA-256；
- exact product snapshot SHA-256；
- canonical Queue SHA-256。

完全相同的 final observation 重跑必须幂等，不生成重复记录。

## Append-only 与 revision

物理结构：

`data/product/m5/operator_history/<trade_date>/<observation_id>.json`

规则：

- 每个 observation 是不可变文件；
- 第一次记录某交易日：revision 1；
- 同一交易日数据/代码/input identity 后续真实变化：追加 revision 2、3…；
- 绝不覆盖旧 revision；
- 比当前同日最新 revision 更旧的 source generated-at 禁止追加；
- 已经存在较新交易日后，禁止向更早交易日做历史 backfill；
- append 过程由跨进程 OS advisory lock 串行化。

这是一条 prospective **product** journal，不是历史回填研究库。

## Delta baseline

跨日 Delta 继续复用 Phase 2 `build_operator_delta` 的产品观察语义。

对于某日任一 revision，其跨日基线固定为：

**上一已记录交易日的最新有效 revision**

而不是“上一文件”或同日上一 revision。

因此同日 revision 不会被误写成一天的 lifecycle transition。

Phase 2 的 current-analysis-error disappearance suppression 继续生效：当前某标的分析失败时，不把其候选缺失误记为 `disappeared_candidate`。

第一个 history 日使用：

`baseline_no_previous_observation`

## 完整性链

每条 observation 自带：

- `record_integrity_sha256`；
- `previous_same_day_observation_id`；
- `previous_recorded_trade_date`；
- `previous_observation_id`。

查询或追加前必须 fail-closed 验证：

- 单记录 schema / contract；
- Queue hash；
- observation identity；
- record self-integrity hash；
- 文件名 == observation id；
- 目录名 == trade date；
- 同交易日 revision ordinal 必须连续 1..N；
- same-day previous link 必须精确指向上一 revision；
- previous trade-date observation 必须存在；
- previous observation 必须是上一已记录交易日的最新 revision。

删除、篡改、断链时，不返回一个“看起来正常”的历史；直接报告 `operator_history_integrity_failure`。

## 查询

`query_operator_history` / GET `/api/operator/history` 支持：

- instrument_id；
- display_key；
- start/end trade date；
- latest revision per day（默认）；
- all revisions；
- summary-only；
- limit。

默认产品界面使用“每天最后一个 revision”，避免同日内部重算淹没跨日复盘；审计时仍可查看全部 revisions。

## 产品入口

- recorder：`scripts/m5_record_operator_history.py`
- query CLI：`scripts/m5_query_operator_history.py`
- 一键查询：`运行HT-CN历史变化查询.bat`
- report：`artifacts/reports/m5-operator-history.json`
- runtime history：`data/product/m5/operator_history/`
- API：GET `/api/operator/history`
- Workbench：**跨日产品观察历史**
- browser gate：`apps/web/tests/operator-history.spec.ts`

工作台历史面板与 Phase 2 “今日变化”并存：
- 今日变化 = 浏览器当前/上一产品快照即时比较；
- 跨日历史 = server-side append-only journal。

二者不能混成一个 authority。

## 永久边界

Phase 11：
- authoritative_transition=false；
- authoritative_evidence=false；
- writes_m4_evidence=false；
- predictive_score_used=false；
- historical_outcome_used_for_ranking=false；
- alpha_inference_allowed=false；
- is_trade_instruction=false；
- mutates_harmonic_identity=false；
- mutates_source_raw_prz=false；
- owns_lifecycle=false。

Runtime `data/product/**` 继续 Git ignored。

## 验证

开发中首轮 CI #1693 / `35384383540`：
- Python 715 passed；
- Web build success；
- 原有 21 Playwright 全部通过；
- 新 history test 因 locator 同时命中两个交易日卡片而失败；
- 该失败是 test strict-mode ambiguity，不是 product semantics failure；
- locator 在 `b49d1468a243f0a129def63b6ee3984170d1ceb8` 收窄到最新日期 card。

后续 CI #1695 / `35384556086`：
- Python 715 passed；
- Web build success；
- Playwright 22 passed。

最终 chain-hardening checkpoint：

`504cc063d93e999dcbac1b131e14f475beacd4d0`

Hosted CI #1699 / `35384764795`：
- overall success；
- Python 718 passed；
- Web build success；
- Playwright 22 passed；
- browser evidence upload success。

Freeze audit：
- M4 capture methodology changed components: 0 / 37；
- Outcome Engine changed components: 0 / 4。
