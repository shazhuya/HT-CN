# M5 Phase 14 — Daily Handoff Bundle v3 / Review-State Transport

status: frozen
validated_code_checkpoint: `c9de28d959b64043663a2bceccb17cc87b8f3756`
validated_ci_run_id: `35416336734`
validated_ci_run_number: `1790`
validation_pr: `#26` (draft CI carrier only)
date: `2026-09-19`

## 目标

建立一个新的 versioned daily handoff transport，把 Phase 11–13 的产品历史、每日变化复盘与人工 review/follow-up 状态安全运输，同时保持 Phase 10 handoff v2 完全冻结。

Phase 14 不修改：
- `src/htcn/app/daily_handoff.py`
- `src/htcn/app/daily_handoff_runner.py`
- `scripts/m5_build_daily_handoff.py`
- `运行HT-CN每日交接包.bat`
- v2 manifest/schema/verification semantics。

v3 是新 transport contract，不是 v2 overwrite。

## 架构

v3 外层 ZIP：

`artifacts/reports/htcn-daily-handoff-v3.zip`

外层 manifest：

`daily-handoff-v3-manifest.json`

v3 的第一层 member 永远是一个**现场重新构建并通过冻结 v2 verifier 的基础包**：

`base/htcn-daily-handoff-v2.zip`

注意：
- v2 只在 v3 build 的临时目录生成；
- 不覆盖旧 `artifacts/reports/htcn-daily-handoff-v2.zip`；
- v3 verifier 会重新调用冻结 v2 verifier；
- v2 内仍然负责 final Operator product snapshot + nested M4 evidence 的原始边界。

因此 Phase 14 没有复制或重新定义 Phase 10 authority。

## Nested v2 binding

v3 manifest 必须保存：

- nested v2 schema version；
- nested v2 bundle SHA-256；
- nested v2 status；
- nested v2 product binding。

verifier 必须把这些字段与真实 nested v2 manifest 一一比对。

另外：
- 外层 pipeline SHA 必须等于 nested v2 中原始 pipeline member bytes 的 SHA；
- 不允许通过重新序列化 JSON 后比较，因为格式差异不能制造假错误。

## Readiness inheritance

v3 从同一份 frozen pipeline report 读取：

- `m5_product_ready`
- `m5_history_ready`
- `m5_review_digest_ready`
- `m4_research_ready`

这些 readiness 只是被运输，不由 v3 重新定义。

永久规则：

- digest ready => history ready；
- history ready => product ready；
- 不满足时 v3 build/verifier 必须 fail closed。

v3 transport failure 不得改写任何上述 readiness。

## Phase 11 history transport

当 `m5_history_ready=true`：

必须绑定**与 nested v2 当前 product snapshot 完全同源**的 latest current-trade-date history record。

current history source 中：
- report SHA
- snapshot SHA
- trade date

必须与 nested v2 `product_binding` 完全一致。

否则：
- `history_product_report_hash_mismatch`
- `history_product_snapshot_hash_mismatch`
- `history_product_trade_date_mismatch`

### 有界 history transport

v3 不打包全部长期 history。

只运输：

1. current latest observation；
2. current record 直接引用的上一交易日 latest observation；
3. current record 如存在 previous_same_day_observation，则运输该直接上一同日 revision。

这样足够离线检查当前 observation 的直接链路，同时避免交接包随历史无限增长。

### Delta 独立复算

如果 current record 有上一交易日 baseline：

verifier 必须使用：
- previous queue_snapshot
- current queue_snapshot

重新运行 frozen Operator Delta 逻辑。

重算结果必须等于 current history record 内保存的 delta。

如果没有上一交易日：
- 不允许出现 previous-history member；
- current delta 必须是 `baseline_no_previous_observation`。

## Phase 12 digest transport

当 `m5_review_digest_ready=true`：

必须运输：

`m5/review/m5-daily-review-digest.json`

builder/verifier 不能只看 digest 自己写的 source id。

必须从 transported current history record 重新构建 Phase-12 digest，并要求：

`artifact_without_transport_metadata == recomputed_digest`

transport metadata 只允许：
- generated_at_utc
- history_root
- report_path

digest 必须继续保持：
- product change triage only；
- no alpha；
- no predictive score；
- no outcome ranking；
- no trade instruction。

## Phase 13 review-session transport

当 Phase-12 digest ready 时，v3 必须捕获一个当前 review-session snapshot：

`m5/review/m5-review-session-snapshot.json`

session 不是持久化 authority 文件，而是 handoff build 时从：
- validated Phase-11 history
- validated Phase-13 review journal

即时导出的 transport snapshot。

### Journal concurrency

导出 session 与选择 journal event chain 时，必须拿 Phase-13 同一个：

`.locks/review-journal.lock`

避免用户刚好写 review event 时出现：
“session 是旧状态、event 文件是新状态”
的撕裂快照。

### Session -> digest projection

移除 Phase-13 专属字段以及 item-level `review` 后：

review session 必须精确投影回 transported Phase-12 digest。

任何不一致：
`review_session_digest_projection_mismatch`

## Review journal event-chain closure

v3 不运输完整 review journal。

root event ids 来自：

- current digest item 的 `current_event_id`
- current digest item 的 `active_follow_up_event_id`
- persistent `active_follow_ups[].event_id`

从这些 roots 开始，递归包含：

- `previous_binding_event_id`
- `previous_display_key_event_id`

直到链首。

因此：
- 当前 session 能被离线验证；
- 不相关的 reviewed 历史不会进入包；
- 仍 active 的跨日 follow-up 会进入包；
- 所需 predecessor 不会丢失；
- 包大小不随整个 journal 无限增长，只随“当前相关链”增长。

verifier 必须保证：

`included_event_ids == closure(root_event_ids)`

少一个 predecessor => invalid。

多带一个不相关 event => invalid。

## Event verification

每个 transported review event 必须继续通过 Phase-13 verifier：

- schema；
- contract boundary；
- event id；
- binding id；
- filename；
- trade-date/binding directory；
- note/state；
- self-integrity SHA。

v3 还必须交叉验证：

### current review event
- observation id == current session source observation；
- display key == item display key；
- review state == session item review state；
- note == session item note。

### active follow-up
- event state == follow_up；
- event source display key / instrument / observation / trade date
  必须与 session active-follow-up item 完全一致。

## Outer manifest boundary

固定：

- schema_version=3
- transport_only=true
- authoritative_evidence=false
- writes_m4_evidence=false
- is_trade_instruction=false
- alpha_inference_allowed=false
- predictive_score_used=false
- historical_outcome_used_for_ranking=false
- review_state_changes_product_ranking=false
- m4_authority_remains_inside_nested_v2_capture_chain=true
- phase10_handoff_v2_is_nested_and_unmodified=true
- review_session_is_product_workflow_only=true

reviewed/follow_up 不能因为被 transport 而获得新的产品或研究含义。

## Status

允许：

- `complete_review_transport`
  - product/history/digest ready；
  - review session + required journal closure included。

- `history_transport_review_degraded`
  - product/history ready；
  - Phase-12 digest not ready；
  - transport history but no Phase-12/13 layer。

- `product_transport_history_degraded`
  - product ready；
  - history not ready；
  - only nested v2 product transport。

- `base_transport_product_failed`
  - product not ready；
  - outer v3 remains a transport wrapper around valid degraded v2。

M4 readiness remains independent inside nested v2.

## Atomic write

v3 与 v2 一样：

1. write temp ZIP；
2. full v3 verify；
3. atomic replace；
4. verify final ZIP again。

任何 pre-replace verify failure 不得产生最终 v3。

## Runner isolation

新增：

`src/htcn/app/daily_handoff_v3_runner.py`

runner：
- 读取 Phase-9/11/12 pipeline report；
- build v3；
- build 前后比较 pipeline report SHA；
- 写独立 report；
- 运输失败只返回自己的 exit code。

report：

`artifacts/reports/m5-daily-handoff-v3.json`

固定声明：

- transport_failure_does_not_rewrite_pipeline_readiness=true
- phase10_handoff_v2_is_not_overwritten=true。

## One-click

新增：

`scripts/m5_build_daily_handoff_v3.py`

`运行HT-CN每日交接包v3.bat`

它只 build v3：
- 不运行 daily-close pipeline；
- 不运行旧 v2 entrypoint；
- 不覆盖旧 v2 ZIP/report。

## 验证

首轮 code CI：

run #1788 / `35416245508`
- overall success；
- Python 771 passed；
- Web build success；
- Playwright 24 passed；
- browser evidence upload success。

final hardening 新增：
- review-event predecessor chain closure transport test；
- forged nested-v2 binding manifest rejection；
- forged pipeline hash manifest rejection。

Final validated code checkpoint：

`c9de28d959b64043663a2bceccb17cc87b8f3756`

Final code CI：

run #1790 / `35416336734`
- overall success；
- Python 774 passed；
- Web build success；
- Playwright 24 passed；
- browser evidence upload success。

Freeze audit：
- Phase-10 handoff v2 files changed: 0；
- M4 capture methodology changed components: 0 / 37；
- Outcome Engine changed components: 0 / 4。

Draft PR #26 只是 hosted-CI / diff audit carrier，不代表已经合并。
