# M2.28 — Standalone AB=CD Source Raw PRZ / v4 Closeout

状态：**Accepted on branch, pending final PR integration**  
功能/研究检查点：`07fde2b1d69664e421b1cb86e3af45a6e26b1093`  
真实 A 股 CI：run `#555` / `35127486034` — success  
研究数据集：`a-share-research-v2-45`，snapshot cutoff `2026-09-15`

## 1. 本阶段修复了什么

M2.28 只解冻 **standalone AB=CD** 的 Source Raw PRZ，不扩张 Shark / 5-0，也不改变已冻结标准 XABCD identity。

Source contract：

- `AB=CD x1` / equivalent AB=CD completion 是 defining measurement；
- Reciprocal BC 是 complementary Source Raw PRZ measurement；
- Volume Three 的 BC layering（例如 1.618 -> 2.0 BC）属于 **execution tolerance / execution refinement**；
- BC layering 明确 `raw_prz_membership = false`、`identity_membership = false`，不得被 UI、scanner 或 research 当成 Raw PRZ 边界；
- Runtime / research 均从 signal-time A/B/C geometry 重建 source measurements，不允许从 legacy Ideal Core 反推 Source PRZ。

API contract 升级为：

- `semantics_version = 3`；
- `source_prz.profile_version = 2`；
- legacy `price_low/high` 继续仅代表 Ideal Core compatibility alias。

## 2. Book / Golden Gate

新增 standalone AB=CD source case ledger 与 deterministic regression：

- 原书 equivalent AB=CD completion 与 reciprocal BC 的 source membership 被机器化；
- source evidence 与 HT-CN engineering execution tolerance 分层；
- regression 明确禁止 Volume Three BC layering 进入 Raw PRZ / identity；
- Alternate Bat 等仍 unresolved/source-conflict 的项目继续 fail closed。

因此 M2.28 的“解冻”不是把 legacy AB=CD zone 改名，而是新增独立 source-backed contract。

## 3. v4 真实 A 股研究结果

M2.28 建立新的 research definition：`m2-source-prz-v4`。

### 3.1 样本与 Terminal Price Bar

- coverage：45 / 45；
- forming signals：8085；
- confirmed completed reactions：174；
- mature Source-Raw-PRZ Terminal events：**1233**；
- Train / Validation / Holdout：**730 / 222 / 258**；
- purged：23；
- Holdout：**sealed，outcomes not exposed**。

Terminal audit status：

- `terminal_price_bar_observed`：1241；
- `no_terminal_price_bar_within_active_horizon`：4554；
- `projection_late_before_signal`：566；
- `source_prz_unresolved`：**1724**。

相对 M2.27 v3：

- mature Source-Raw-PRZ T-Bar：166 -> **1233**；
- `source_prz_unresolved`：6547 -> **1724**。

这是定义范围扩张后的描述性变化，不允许被解释成 v4 相比 v3 的确认性“性能提升”。

### 3.2 样本扩张来自哪里

standalone AB=CD 在各 split 中占：

- Train：627 / 730；
- Validation：198 / 222；
- sealed Holdout：226 / 258。

因此本阶段的大幅样本增加主要来自 standalone AB=CD 获得 source-backed Raw PRZ，而不是标准 XABCD 候选突然膨胀。

## 4. Type-I v4 可见证据

T-Bar 后可见 split 的描述性结果：

- Train：T1 `0.5342`，T2 `0.2932`，full Raw PRZ exit <=T+3 `0.3726`，<=T+5 `0.4726`；
- Validation：T1 `0.5946`，T2 `0.3784`，full Raw PRZ exit <=T+3 `0.3604`，<=T+5 `0.4775`。

Holdout outcome 未打开。

### 4.1 Robustness

6 个预声明 early-path candidates 中，**只有 `full_prz_exit_by_t5` 通过当前 visible robustness gate**：

- Train baseline pending：670，later-T2 rate `0.22985`；gated pending：290，rate `0.29310`；lift **+6.33 pct**；
- Validation baseline pending：192，rate `0.28125`；gated pending：77，rate `0.38961`；lift **+10.84 pct**；
- 当前 robustness blockers：none；
- 通过 visible sample floor、concentration、leave-one-symbol-out、family、direction、temporal、scale checks。

这仍然只是 **v4 visible Train/Validation 下的研究证据**。它不是：

- 当前个股命中概率；
- 自动买卖规则；
- 新的 confirmatory result；
- 对历史 v1 Holdout / external replication 的替代。

### 4.2 T+3 vs T+5 速度分层仍未解冻

`type_i_exit_timing` 正确返回：

- `type_i_exit_timing_not_ready_holdout_sealed`；
- selected hypothesis：none。

原因：nested timing 模块要求 `full_prz_exit_by_t3` 与 `full_prz_exit_by_t5` **同时 robust** 后，才允许拆分 fast / T+4~T+5 / no-exit。v4 只有 T+5 robust，因此不能把“5 bars”升级成 source rule、universal deadline 或 policy。

## 5. 研究版本边界

v4 boundary guard 已通过：`source_prz_v4_research_boundary_verified`。

冻结规则：

- historical v1 Holdout 不重算；
- historical external replication 不重算；
- M2.27 v3 不重贴 v4 标签；
- legacy Ideal Core fallback 禁止；
- cross-version confirmatory comparison 禁止；
- v4 当前 `confirmatory_inference_allowed = false`；
- v4 当前 `eligible_to_replace_historical_v1 = false`；
- 若未来需要 v4 confirmatory conclusion，必须使用新的 untouched future dataset / protocol。

历史 closed evidence 只继续作为其原定义下的冻结事实：

- 45-symbol historical Holdout：exposure 40/115 = 34.78%，comparator 39/198 = 19.70%，effect +15.09 pct，Newcombe 95% CI +4.96..+25.41；
- independent 60-symbol historical replication：257/736 = 34.92% vs 213/1182 = 18.02%，effect +16.90 pct，95% CI +12.83..+20.99。

这些数字 **不得** 重新解释成 v4 standalone AB=CD 的验证结果。

## 6. 完成反应质量研究没有新增 policy

completed-reaction visible evidence 本轮：

- actionable 86；purged 1；Train 51 / Validation 17 / sealed Holdout 17；
- robustness 最终 `robust_candidates = []`。

因此 geometry-top-quartile / fast-confirmation 等可见方向性结果不冻结为生产 gate。

## 7. CI / 工程观察

run #555 首次 v4 research 较慢，主要原因之一是 A-share snapshot cache miss；历史 artifact bootstrap 又因 GitHub integration 权限返回 `Resource not accessible by integration`，于是 45 个 symbols 重新从 BaoStock 获取。

本次 run 结束后新 cache 已成功保存。该问题属于 CI resilience / performance，不改变研究语义与本轮结果；除非再次触发 cache-miss failure，否则不在 Source Fidelity 阶段引入高风险性能重构。

另已识别：大量 source-resolved events 会放大 per-record frame sort / linear target scan 的成本。未来可做结果完全等价的性能优化，但不得与 source definition change 混在一个研究版本中。

## 8. 验收

M2.28 branch acceptance：

- Python deterministic tests ✅
- Web build ✅
- Playwright deterministic browser acceptance ✅
- standalone AB=CD Source PRZ / API contract tests ✅
- Book Golden Gate ✅
- real 45-symbol A-share v4 calibration ✅
- Terminal Price Bar v4 ✅
- Type-I v4 + robustness ✅
- v4 sealed boundary ✅
- historical Holdout integrity ✅
- external replication integrity ✅
- completed-reaction quality/robustness integrity ✅

## 9. 对 M3 的约束

M2.28 **不授权恢复旧 M3 Phase 2 overlay 语义**。

后续工作台如展示 standard XABCD / standalone AB=CD Type-I：

- target anchor 必须来自 source execution clock / Terminal Price Bar；
- Raw PRZ 与 Ideal Core 必须分画/分名；
- PEZ 只能在 T-Bar 形成后出现；
- 不得再用 right-confirmed D Pivot 作为 Type-I 时间原点；
- 不得把 v4 `full_prz_exit_by_t5` visible robustness 写成个股预测概率或机械交易倒计时。

Shark / 5-0 继续遵守 pattern-specific contract / quarantine，不得强行走通用 XABCD execution clock。

## 10. 下一步

Source Fidelity Gate 仍未关闭。

下一批主任务定为 **M2.29 — 5-0 Volume Two / Volume Three Source Reconciliation**：

1. 保持 5-0 production quarantine；
2. 逐图例核对 V2 structural PRZ：50% BC + Reciprocal AB=CD；
3. 独立建模 V3 conditional execution refinement / 61.8 make-or-break；
4. 禁止重新退化成 universal 50%-61.8 identity band；
5. 建立 Book Golden regression 后再决定是否恢复 source-certified identity/execution output。

M2.29 完成后，再继续 Shark terminal-side source freeze / RSI BAMM dedicated module，并最终解除 M3 execution-overlay Gate。
