# M5 Phase 12 — Daily Review Digest / Change Triage v1

status: frozen
validated_code_checkpoint: `84c7d8a0f2d46cd8ed9b79dcd638cb727d165465`
validated_ci_run_id: `35413656027`
validated_ci_run_number: `1733`
validation_pr: `#24` (draft CI carrier only)
date: `2026-09-19`

## 目标

把 Phase 11 已冻结的 append-only Operator History 转成每天可直接阅读、筛选、钻取的产品复盘摘要。

Phase 12 只做：
- 变化计数；
- 既有 workflow bucket 归类；
- change-type 标签；
- 分析不完整标的提示；
- presentation-only 过滤；
- Queue / history / 单票工作台之间的产品导航。

它不把历史 observation 转换为：
- 胜率；
- 收益概率；
- alpha；
- predictive score；
- outcome-based ranking；
- 买卖排序；
- trade instruction。

## Source

唯一 source 是 Phase 11 latest valid Operator History revision。

`build_latest_daily_review_digest` 通过 `query_operator_history(... latest_revision_per_day=True, summary_only=False, limit=1)` 读取最新交易日最后一个 revision。

因此 Phase 12 自动继承 Phase 11 的：
- record self-integrity SHA；
- same-day revision chain；
- previous-trade-date chain；
- no-backfill；
- latest-revision-per-day；
- missing/tampered/deleted history fail-closed。

若 Phase 11 history integrity 失败，Phase 12 不得生成“部分看似正常”的 digest。

## Exhaustive Delta guard

Digest 只能从完整、未过滤的 latest Delta 构建。

必须满足：
- history observation `delta_total_change_count`；
- history observation `change_count`；
- 实际 `changes[]` 长度；

三者完全一致。

任何不一致必须 fail closed：
`operator history latest observation is not an exhaustive unfiltered delta`

因此 UI/API 的筛选永远发生在完整 digest 之后，不能让过滤结果反过来定义“当天真实发生了多少变化”。

## Review ordering

固定 review workflow order：

1. `execution_evaluation`
2. `reaction_observation`
3. `waiting`
4. `evidence_insufficient`
5. `disappeared_candidate`

这是 Phase 1 已有产品工作流顺序的延续，只表示复盘导航顺序。

永久声明：
`ordering_is_product_workflow_not_expected_return=true`

它不是机会排名、收益排名、成功率排名或交易优先级预测。

每个变化 item 必须保留其完整 `change_types[]`，不能因为展示分桶而丢掉同一候选上的次级变化。

## Change types

透明 change-type vocabulary：

- `new_candidate`
- `disappeared_candidate`
- `action_state_changed`
- `lifecycle_state_changed`
- `pattern_state_changed`
- `next_key_changed`
- `execution_gate_changed`
- `context_cautions_changed`

Digest 输出：
- `change_count`
- `change_type_counts`
- `workflow_bucket_counts`
- `workflow_sections`
- `analysis_incomplete_instruments`

`all_changes_are_retained=true`

## Analysis gaps

Phase 2/11 的 current-analysis-error disappearance suppression 继续有效。

Phase 12 把：
`comparison_incomplete_instruments`

单独作为：
`analysis_incomplete_instruments`

呈现。

分析失败标的不得被重解释为：
- 候选消失；
- 生命周期恶化；
- 看空；
- 交易退出信号。

## Digest status

允许：
- `no_history`
- `baseline`
- `no_changes`
- `no_changes_with_analysis_gaps`
- `changes_ready`
- `changes_ready_with_analysis_gaps`

首个 history 日可以是 `baseline`，它表示已有可复盘产品状态，但没有上一交易日作为 Delta baseline。

## Pipeline ordering

每日流水线顺序：

1. M1 market update；
2. M3 context sync；
3. initial M5 Operator cache；
4. independent M4 research lane；
5. final M5 cache revalidation；
6. Phase 11 Operator History append；
7. **Phase 12 Daily Review Digest build**。

Digest 只有在 `m5_operator_history` 成功时才运行。

`m5_daily_review_digest` failure：
- 不得改写 `m5_product_ready`；
- 不得改写 `m5_history_ready`；
- 不得改写 `m4_research_ready`；
- 只令 `m5_review_digest_ready=false`。

## Presentation filters

GET `/api/operator/review-digest` 支持：
- workflow_bucket；
- change_type；
- instrument_id。

过滤规则：
- 只产生 `filtered_workflow_sections`；
- 只改变 `filtered_change_count`；
- 原 `change_count` 永久保留；
- `source_change_count_unchanged` 显式回传。

未知 workflow bucket / change type 必须返回参数错误，不得静默变成 0 条。

这样可以区分：
“今天真的没有变化”
与
“筛选条件没有命中”。

## Product UI

Workbench 新增 **每日变化复盘**，置于跨日产品观察历史之前。

UI 必须同时展示：
- 日期；
- previous trade date；
- revision；
- 源变化总数；
- 当前筛选命中；
- 分析不完整数量；
- change-type counts；
- workflow sections；
- lifecycle/action/next-key before -> after；
- 单票跳转。

固定说明：
“顺序只表示先看哪类变化，不是收益率、胜率或买卖排名。”

## Product entrypoints

- core: `src/htcn/app/daily_review_digest.py`
- daily builder: `scripts/m5_build_daily_review_digest.py`
- report: `artifacts/reports/m5-daily-review-digest.json`
- one-click: `运行HT-CN每日变化复盘.bat`
- API: GET `/api/operator/review-digest`
- UI: `DailyReviewDigest.tsx`
- browser gate: `apps/web/tests/daily-review-digest.spec.ts`

Phase 10 handoff v2 不修改。若未来需要运输 Phase 11/12 artifacts，必须建立新的 versioned handoff contract。

## 永久边界

Phase 12 contract：
- semantics=`product_change_triage_only`；
- exhaustive_changes=true；
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

## 验证

首轮 code CI：

run #1725 / `35413513169`
- overall success；
- Python 733 passed；
- Web build success；
- Playwright 23 passed；
- browser evidence upload success。

随后增加：
- exhaustive latest-Delta count guard；
- invalid workflow/change-type explicit rejection。

最终 validated code checkpoint：

`84c7d8a0f2d46cd8ed9b79dcd638cb727d165465`

Hosted CI #1733 / `35413656027`：
- overall success；
- Python 736 passed；
- Web build success；
- Playwright 23 passed；
- browser evidence upload success。

Freeze audit：
- M4 capture methodology changed components: 0 / 37；
- Outcome Engine changed components: 0 / 4。

Draft PR #24 只作为 hosted-CI / diff audit carrier，不代表已经合并到 Phase 11 或 main。
