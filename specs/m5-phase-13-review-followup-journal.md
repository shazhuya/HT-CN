# M5 Phase 13 — Review Session / Follow-up Journal v1

status: frozen
validated_code_checkpoint: `4b015dfc0e72db0f1275e1e570d85959254550fa`
validated_ci_run_id: `35415145067`
validated_ci_run_number: `1768`
validation_pr: `#25` (draft CI carrier only)
date: `2026-09-19`

## 目标

在 Phase 12 的每日变化复盘之上增加一个**完全独立的产品复盘工作流层**：

- 未看；
- 已看；
- 后续跟踪；
- 可选备注；
- 跨日持续跟踪清单；
- append-only 审计 journal。

Phase 13 记录的是“用户有没有看、是否要继续跟踪”，不是 harmonic / lifecycle / action / research state，也不是仓位、买卖或交易执行状态。

## Source binding

每个 review event 必须绑定：

- `source_observation_id`；
- `display_key`。

写入前必须从 Phase 11 validated Operator History 中确认：
- observation 存在；
- display key 确实是该 observation 的 Delta change；
- instrument id / trade date / revision / change types 可被恢复。

不存在的 observation/display-key binding 必须拒绝。

这保证 review journal 永远引用真实产品变化，而不是浏览器自己制造一个不存在的候选。

## Review state

固定 states：

- `unseen`
- `reviewed`
- `follow_up`

语义：

### unseen
对某个新的 `source_observation_id + display_key`，若没有 journal event，默认就是 `unseen`。

默认未看不需要写事件。

显式保存 `unseen` 可以作为“重置复盘状态”事件。

### reviewed
只表示这个产品变化已经被用户复核。

它不得解释为：
- 看多；
- 看空；
- 通过；
- 失败；
- 买入；
- 卖出；
- lifecycle transition。

### follow_up
只表示这个 display key 需要继续人工复盘。

它不得改变 Queue 排序，也不得自动升级/降级 action 或 lifecycle。

## 当天状态与跨日跟踪必须分离

当前交易日 review state 绑定精确 observation。

因此：

- 昨天“已看”不能让今天的新变化自动变成“已看”；
- 今天出现新的 observation/change 时，如果今天尚未写 event，仍显示 `unseen`。

同时 follow-up 连续性按 display key 计算：

- 每个 display key 的最新 review event 如果是 `follow_up`，则视为 active follow-up；
- active follow-up 可以跨 observation / trade date 持续；
- 如果第二天没有新 Delta，它仍必须留在“持续跟踪清单”；
- latest display-key event 变为 `reviewed` 或 `unseen` 后，active follow-up 结束。

因此系统同时保留：
1. “今天这条新变化看过没有”；
2. “这个结构是否仍在持续跟踪”。

二者不得混成一个状态。

## Append-only journal

runtime root：

`data/product/m5/review_journal/`

event path：

`<trade_date>/<binding_id>/<event_id>.json`

其中：

`binding_id = SHA256(source_observation_id + display_key)`

所有 event 不覆盖旧文件。

写入使用跨进程 OS advisory lock。

## Idempotency

每个写请求必须提供 `client_request_id`。

同一 request id：

- payload 完全一致 → 返回 `idempotent_existing`；
- payload 不一致 → `client_request_id replay conflict`。

这样浏览器/API 因网络重试不会制造重复 review event。

## Note

备注：
- 可为空；
- CRLF 正规化为 LF；
- trim；
- 最大 1000 字符。

Phase 13 只把 note 当人工复盘文本保存，不做 sentiment / alpha / outcome 解析。

## Event integrity

每个 event 包含：

- event id；
- self-integrity SHA-256；
- binding event ordinal；
- display-key event ordinal；
- previous binding event id；
- previous display-key event id。

加载 journal 时 fail closed 检查：

- schema；
- contract boundary；
- binding hash；
- review state；
- note；
- request id；
- event id；
- filename；
- trade-date/binding directory；
- self-integrity hash；
- binding ordinal 连续性；
- binding previous link；
- display-key ordinal 连续性；
- display-key previous link；
- client request id 唯一性。

中间事件删除、链断裂或内容篡改必须返回：

`review_journal_integrity_failure`

不得静默跳过坏 event。

## Active follow-up

`query_active_follow_ups` 从每个 display key 的最新 valid event 推导 active list。

active follow-up list：
- 不依赖当天是否出现新 Delta；
- 记录 source observation / source trade date；
- 记录 instrument / display key；
- 记录 latest follow-up note；
- 标记 `in_current_digest`。

Workbench 中：
- 同日刚 follow-up 显示“跟踪中”；
- source trade date 早于 current trade date 时显示“跨日跟踪中”；
- 没有新变化的 active follow-up 仍显示；
- 可直接点击“结束跟踪”。

结束跟踪会写一个新的 `reviewed` event，不删除历史 follow-up event。

## Review session

GET `/api/operator/review-session`

返回：
- Phase 12 完整 digest；
- current review state；
- review-state counts；
- active follow-up list/count；
- current-digest active follow-up count；
- filtered review sections。

过滤支持：
- workflow bucket；
- change type；
- instrument；
- review state；
- follow-up only。

所有过滤都是 presentation-only。

源：
- `change_count`
- `review_state_counts`
- `active_follow_up_count`

必须继续保留，不得因筛选而改写。

## Write API

POST `/api/operator/review-session/event`

必须提供：
- source_observation_id；
- display_key；
- review_state；
- client_request_id。

可选：
- note。

API 不返回本地 filesystem path。

返回固定声明：
- authoritative_evidence=false；
- writes_m4_evidence=false；
- is_trade_instruction=false。

## Read-only audit

GET `/api/operator/review-journal`

支持：
- display key；
- instrument；
- source observation；
- review state；
- limit。

CLI：

`scripts/m5_query_review_journal.py`

one-click：

`运行HT-CN复盘跟踪查询.bat`

查询只读，不生成 event。

## Workbench

Phase 12 的“每日变化复盘”升级为 Review Session，但 Phase 12 digest contract 本身不修改。

Workbench 新增：

- 未看 / 已看 / 当天后续跟踪 counts；
- 持续跟踪中 count；
- review-state filter；
- follow-up-only filter；
- item-level state selector；
- 最长 1000 字 note；
- 显式“保存复盘”；
- 独立“持续跟踪清单”；
- “结束跟踪”。

浏览器 localStorage 不拥有 review state。

所有权威产品复盘状态来自 server-side review journal。

## Pipeline boundary

Phase 13 **不加入 daily-close pipeline**。

原因：

review events 是明确的用户交互行为，没有用户动作时不应由定时流水线自动制造 reviewed/follow_up event。

因此：
- Phase 9/11/12 readiness 不依赖 Phase 13；
- Phase 13 failure 不得改写 product/history/digest/research readiness；
- daily close 仍可在没有任何 review event 的情况下成功。

## Frozen non-authority contract

Review journal 永久声明：

- semantics=`product_review_workflow_only`
- append_only=true
- authoritative_transition=false
- authoritative_evidence=false
- writes_m4_evidence=false
- predictive_score_used=false
- historical_outcome_used_for_ranking=false
- alpha_inference_allowed=false
- is_trade_instruction=false
- mutates_operator_queue=false
- mutates_operator_history=false
- mutates_action_state=false
- mutates_lifecycle=false
- mutates_harmonic_identity=false
- mutates_source_raw_prz=false

Review state 或 follow-up 状态不得用于：
- Queue 排序；
- alpha；
- win rate；
- predictive score；
- candidate quality score；
- trade instruction；
- lifecycle/action upgrade。

## Phase 10 handoff

Phase 10 handoff v2 继续冻结不变。

Phase 13 不修改 v2 transport contract。

未来如需运输：
- Phase 11 history；
- Phase 12 digest；
- Phase 13 journal/session；

必须建立新的 versioned handoff contract。

## 验证

首轮 CI：

run #1766 / `35415053453`

结果：
- Python 757 passed；
- Web build success；
- 原有 23 Playwright passed；
- 新增 Phase-13 test 仅因 “今日有新变化” 同时命中 list header 和 item row 导致 strict locator failure；
- 产品写入/跟踪逻辑没有失败。

locator 在：

`4b015dfc0e72db0f1275e1e570d85959254550fa`

收窄到具体 follow-up row。

最终 validated code checkpoint：

`4b015dfc0e72db0f1275e1e570d85959254550fa`

Hosted CI #1768 / `35415145067`：
- overall success；
- Python 757 passed；
- Web build success；
- Playwright 24 passed；
- browser evidence upload success。

Freeze audit：
- M4 capture methodology changed components: 0 / 37；
- Outcome Engine changed components: 0 / 4。

Draft PR #25 只是 hosted-CI / diff audit carrier，不代表已经合并到 Phase 12 或 main。
