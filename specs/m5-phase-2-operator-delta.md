# M5 Phase 2 — Operator Delta / 今日变化

状态：**Product-layer observation contract; not M4 authoritative evidence**

## 1. 目标

Phase 1 回答“现在有哪些候选、当前在哪”。

Phase 2 回答：

> 相比上一交易日，哪些产品状态发生了值得人工关注的变化？

允许观察：

- new_candidate
- disappeared_candidate
- action_state_changed
- lifecycle_state_changed
- pattern_state_changed
- next_key_changed
- execution_gate_changed
- context_cautions_changed

不允许把这些 product changes 写成 M4 authoritative transition。

## 2. Product-only contract

固定：

- semantics = product_observation_only
- authoritative_transition = false
- writes_m4_evidence = false
- predictive_score_used = false
- historical_outcome_used = false
- alpha_inference_allowed = false
- is_trade_instruction = false
- mutates_harmonic_identity = false
- mutates_source_raw_prz = false
- owns_lifecycle = false

## 3. Stable product identity

Phase 1 display key 使用 bar index 时，固定长度窗口滚动可能使 index 改变。

Phase 2 起，product display identity：

- 优先使用 harmonic point trade_date；
- trade_date 缺失时才 fallback 到 index；
- 还包含 instrument / pattern / schema / direction / scale。

它只服务产品比较，不取代 M4 candidate identity。

## 4. Queue snapshot schema v2

Queue 顶层新增：

- as_of_trade_date
- observed_trade_dates
- observation_integrity

规则：

- 所有成功分析标的 last_trade_date 唯一时：single_as_of；
- 多日期：mixed_as_of；
- 没有日期：empty。

只有 single_as_of 可以进入 Operator Delta。

## 5. Chronology

- current < previous：拒绝；
- current == previous：same_as_of_no_delta；
- current > previous：允许比较。

同交易日刷新不会制造“今日变化”。

## 6. Error isolation

如果当前某 instrument 分析失败：

- 该 instrument 进入 comparison_incomplete_instruments；
- 对其旧 candidate 的 disappeared_candidate 判定被抑制；
- 不能把数据错误冒充 candidate disappearance。

## 7. Snapshot persistence

浏览器 localStorage 只保留最近两个 product snapshots：

- htcn.operator.queue.current.v2
- htcn.operator.queue.previous.v2

它们：

- 不是 M4 evidence；
- 不上传研究链；
- 可由用户重置；
- 只用于产品变化展示。

“显示证据不足”只做 UI 过滤；后台始终获取并保存完整 Queue，避免过滤器制造伪 disappearance。

## 8. API

新增：

POST /api/operator/delta

输入：

- previous queue snapshot
- current queue snapshot

输出：

- date range
- product contract
- change count/type counts
- changes
- incomplete instruments
- warnings

API 本身不持久化任何 snapshot。

## 9. UI

新增：

**今日变化**

显示：

- 两个交易日范围；
- candidate change count；
- change badges；
- previous/current action + lifecycle；
- previous/current next-key；
- 数据失败导致的 incomplete warning；
- 点击 instrument 进入单票深挖。

## 10. 验收

Hosted CI checkpoint：

`791cbdb18322a9fc00e771b9bcb79529d8e63277`

Actions run #1503：

- overall success；
- Python: 619 passed；
- Web build: success；
- Playwright: 19 passed；
- browser evidence upload: success。

冻结边界：

- M4 methodology changed = 0；
- Outcome Engine changed = 0。
