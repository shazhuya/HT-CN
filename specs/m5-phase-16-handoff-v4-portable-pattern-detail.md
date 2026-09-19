# M5 Phase 16 — Handoff v4 / Portable Pattern Drill-down Transport v1

状态：**implementation in progress**

## 1. 目标

Phase 15 已证明 v3 可以在没有本机行情库的环境中可靠复盘 Queue / History / Digest / Review 状态。

Phase 16 补齐下一层缺口：

> v3 当前 Queue 只有产品摘要，没有完整 K 线与 pattern.points，因此不能在纯离线环境中真实重建 XABCD / 0XABC / PRZ / T-Bar 图形。

Phase 16 不修改冻结的 Phase-14 v3，也不修改 Phase-15 inspector contract，而是建立一个新的 versioned transport：

`htcn-daily-handoff-v4.zip`

v4 = **原样嵌套的 verified v3 + 当前 Queue 候选对应的 exact portable pattern detail**。

## 2. Source binding

构建 v4 前必须满足：

1. v3 通过 `verify_daily_handoff_bundle_v3()`；
2. v3 当前 product snapshot 存在 input identity；
3. 构建时本机 current input identity fingerprint 与 v3 snapshot fingerprint 完全相同；
4. 分析结果 `last_trade_date` 与 v3 trade date 完全相同。

任一失败，禁止生成正式 v4。

该约束防止：

- 用更新过的行情给旧 Queue 画图；
- 用更新过的分析代码重算旧 transport；
- 跨交易日混合 detail。

## 3. Detail inclusion policy

Phase 16 不做 top-N，也不按预期收益筛选。

唯一 inclusion set：

**v3 current Operator Queue 中全部 display keys。**

对每个 Queue display key，v4 必须二选一：

- exact portable detail；
- explicit portable detail error。

禁止静默漏项。

验证要求：

`detail_keys ∪ error_keys == current_queue_keys`

且：

`detail_keys ∩ error_keys == ∅`

## 4. Exact pattern binding

每个 portable detail 都来自当前 M3 analysis payload。

只允许：

- primary identity；
- display key 与 Operator Queue 的稳定 key 完全一致；
- transported pattern payload 的 points 自己重新推导出的 display key 与声明 key 完全一致。

v4 不允许：

- 用 instrument + pattern_id 模糊匹配；
- 用“最近一个同类形态”替换；
- 补造未来 D；
- 把 secondary identity 当成新的独立 Queue 候选。

## 5. Transport structure

```
daily-handoff-v4-manifest.json
base/
  htcn-daily-handoff-v3.zip
detail/
  instruments/
    <instrument>.json
  errors.json
```

每个 instrument detail：

- instrument_id；
- trade_date；
- bars；
- exact current-Queue patterns；
-完整 pattern payload，包括：
  - points；
  - PRZ；
  - source_lifecycle；
  - decision_narrative；
  - reaction audit / targets（若原 analysis 有）；
- price_mode / warning；
- display-key list。

## 6. Boundary

固定 contract：

- nested_v3_unmodified=true
- queue_semantics_changed=false
- detail_changes_ranking=false
- authoritative_evidence=false
- writes_m4_evidence=false
- writes_operator_queue=false
- writes_operator_history=false
- writes_review_journal=false
- creates_review_events=false
- predictive_score_used=false
- historical_outcome_used_for_ranking=false
- alpha_inference_allowed=false
- is_trade_instruction=false

v4 是 portable presentation transport，不是新的 methodology authority。

## 7. Portable visual Inspector

新增 v4 inspector：

`src/htcn/app/handoff_v4_inspector.py`

离线 HTML：

`artifacts/reports/m5-handoff-v4-pattern-workspace.html`

图形最小语义：

- K 线来自 transported bars；
- 已存在 pattern.points 用实线连接；
- 节点直接显示 **字母 + 价格**；
- Source PRZ 以阴影区显示；
- Source T-Bar / T+1 / T1 / T2 / Type-II T-Bar / II Exit 使用事件线；
- 下一关键价显示为**虚线水平导引**；
- 虚线导引明确标注“不是预测腿”；
- forming pattern 不允许补造未来 D 或潜在 leg。

因此 Phase 16 同时关闭早期 UI 的两个长期欠账：

1. 节点只显示 X/A/B/C/D、不显示价格；
2. 为了“看完整”而把尚未发生的未来腿画成已知结构。

## 8. 一键入口

`scripts/m5_build_portable_pattern_workspace_v4.py`

Windows：

`运行HT-CN便携图形复盘v4.bat`

默认产物：

- `artifacts/reports/htcn-daily-handoff-v4.zip`
- `artifacts/reports/m5-handoff-v4-inspector.json`
- `artifacts/reports/m5-handoff-v4-pattern-workspace.html`

## 9. Acceptance

- [ ] v3 invalid -> v4 fail closed；
- [ ] input identity mismatch -> v4 fail closed；
- [ ] all Queue display keys exhaustively covered by detail or explicit error；
- [ ] no extra detail key outside current Queue；
- [ ] exact pattern key can be re-derived from transported points；
- [ ] v4 verifier detects semantic tamper even when outer member hash is updated；
- [ ] v4 inspector requires no market DB；
- [ ] node label includes price；
- [ ] Source PRZ / lifecycle event can render from transport；
- [ ] forming pattern does not invent future D；
- [ ] next-key dashed line is guide, not projected pattern leg；
- [ ] Python regression green；
- [ ] existing Web build green；
- [ ] existing Playwright gates green；
- [ ] M4 methodology drift = 0；
- [ ] Outcome Engine drift = 0。
