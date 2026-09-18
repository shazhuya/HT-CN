# M4 Phase 3.1 — Outcome Evidence v2 / Engine Freeze / Offline Recompute

状态：**Frozen before first real prospective outcome**

日期：2026-09-18

## 1. 目标

Phase 3.1 不增加交易策略，也不做胜率、收益率、alpha 或排名。

目标只有一个：

**把已预注册的 prospective outcome 定义变成可重复、可独立复算、可检测数据修订和实现漂移的 evidence chain。**

Phase 3.1 永久分离三种身份：

1. **Capture methodology identity**
   - 决定 candidate identity、Source Raw PRZ、Source lifecycle、prospective enrollment；
   - methodology contract v4；
   - committed capture schema v5；
   - prospective observation schema v4；
   - 37 components；
   - exact freeze commit：
     `c774c54928c33361952bf1a612a8555633449625`。

2. **Outcome protocol identity**
   - 决定 outcome 要观察什么事实、窗口和 censoring；
   - 当前 active protocol：`m4-outcome-v2`；
   - canonical SHA-256：
     `5822b302e11d197682dc4bb6d835fb0a3b2d62fc97f788c7a323ecda2770555b`。

3. **Outcome engine identity**
   - 决定用哪一版代码把 enrollment seed + market path 转换成 outcome facts；
   - engine contract v1；
   - 4 components；
   - exact code anchor：
     `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`。

这三种身份不得互相代替。

---

## 2. 为什么 v2 supersede v1

`m4-outcome-v1` 是有效的历史 preregistration，保留不改写。

在第一笔真实 prospective outcome 出现之前，Phase 3.1 实现审计发现：

原 v1 的 MFE/MAE 直接差值公式，在整个 post-terminal window 都没有越过 Terminal price 时，理论上可能产生负 excursion。

标准 MFE/MAE 应表示非负幅度。

因此在**尚无任何真实 prospective outcome evidence**时，创建 `m4-outcome-v2`，显式 supersede v1：

- v1 文件与 fingerprint 永久保留；
- v1 validator 仍可用于历史复现；
- v2 采用 nonnegative magnitude；
- v2 对 excursion 做 zero floor；
- 不静默修改 v1；
- 不把 v1 结果迁移成 v2，因为当时没有真实 outcome result。

v2 公式：

Bullish:

- MFE = `max(0, max(post_terminal_high) - terminal_price)`
- MAE = `max(0, terminal_price - min(post_terminal_low))`

Bearish:

- MFE = `max(0, terminal_price - min(post_terminal_low))`
- MAE = `max(0, max(post_terminal_high) - terminal_price)`

---

## 3. Outcome path

Outcome evaluator 不使用 capture snapshot index 代替交易日。

正式路径来自：

`M1 base + daily_delta logical daily history`

规则：

- 使用真实 traded bars；
- full-day suspension 不伪造 OHLC，不计作 traded bar；
- path 从 frozen source signal date 开始重建；
- outcome as-of 之后的 bar 不可见；
- duplicate trade date fail closed；
- 非 finite / 非法 OHLCV fail closed；
- price basis 必须与 enrollment formal QFQ basis 一致；
- 已观察到 basis drift 时，不尝试使用当前 QFQ 历史去“回算”旧标尺。

---

## 4. Source-event reconstruction

Evaluator 必须复用已有核心：

- `htcn.harmonic.execution.observe_source_execution`
- `htcn.harmonic.source_lifecycle.derive_source_lifecycle`

禁止复制第二套 Terminal / Type-I / Type-II 公式。

输入来自 frozen enrollment seed：

- pattern_id / schema / direction / scale；
- Source Raw PRZ；
- source signal trade date；
- source signal clock basis；
- reaction anchor label / price。

可输出的 primary source facts：

- first Source PRZ entry；
- Source Terminal observed / not observed；
- terminal trade date / price；
- 38.2% / 61.8% target；
- first hit offset；
- T+1...T+5 Type-I classification；
- reaction-only later 38.2%；
- first Source PRZ exit；
- Type-II re-entry；
- strict terminal-side retest；
- post-Type-II reversal-direction exit。

若重建 Terminal 在 outcome enrollment 当日或之前出现：

**evidence_contradiction**

不得作为正常 prospective outcome。

---

## 5. Carney source fact 与 HT-CN engineering metric 分层

Source-aligned：

- Terminal Price Bar；
- Type-I first reaction；
- 38.2% / 61.8% automatic objectives；
- secondary PRZ retest 的 Type-II price structure。

HT-CN engineering：

- M1 logical history；
- QFQ price-basis fingerprint；
- 5 / 10 / 20 traded-bar descriptive windows；
- canonical OHLCV path hash；
- immutable outcome snapshots；
- outcome engine fingerprint。

Type-II price structure **不是**完整 Carney Type-II reversal proof。

没有单独冻结 indicator-confirmation protocol 时：

`full_carney_type_ii_reversal_claim_allowed=false`

Shark 的 generic Type-I 38.2% / 61.8% 只用于 canonical lifecycle classification：

`shark_generic_type_i_is_management_target=false`

Shark-specific 50% / Reciprocal AB=CD management target 不在 outcome-v2。

---

## 6. Descriptive path windows

固定窗口：

- 5 traded bars：primary；
- 10 traded bars：secondary；
- 20 traded bars：secondary。

窗口：

- 从 T+1 开始；
- 不包含 Terminal bar；
- 未完整观察对应 traded bars 时为 `immature`；
- 不用 partial window 冒充完整 window。

记录：

- MFE price；
- MAE price；
- MFE / MAE terminal %；
- MFE / MAE reaction-span units。

reaction span：

`abs(reaction_anchor_price - terminal_price)`

---

## 7. Self-contained canonical market path

每个 outcome result 必须保存：

- `market_path_trade_dates`
- `market_path_traded_bar_count`
- `market_path_rows`
  - trade_date
  - open
  - high
  - low
  - close
  - volume
- `current_price_basis_id`
- `market_path_sha256`

hash 输入：

**canonical trade_date + OHLCV + price_basis_id**

这意味着 evidence bundle 离开私有 M1 电脑后，仍可：

1. 重建 DataFrame；
2. 独立重算 path hash；
3. 使用 frozen enrollment seed 重跑 evaluator；
4. 对账 Source events 与 descriptive windows。

只保存 hash、不保存 hash 输入，不满足 Phase 3.1 独立审计要求。

---

## 8. Immutable outcome snapshot schema v2

Outcome snapshot schema：**v2**

每个 snapshot 绑定：

- outcome as-of trade date；
- outcome protocol ID + fingerprint；
- capture methodology fingerprint；
- outcome engine contract version + fingerprint；
- complete candidate result set；
- deterministic snapshot ID。

规则：

- 同 as-of + 相同事实：幂等；
- 同 as-of + 不同事实：data drift，fail closed；
- 历史 outcome backfill：fail closed；
- 一个 outcome store 不能混：
  - protocol identity；
  - capture methodology identity；
  - outcome engine identity。

若任一 identity 改变：

**必须开启显式新 outcome epoch，不得把新实现继续写入旧 evidence chain。**

---

## 9. Outcome Engine Identity

Engine contract v1 由 4 个文件组成：

1. `src/htcn/research/outcome_protocol.py`
2. `src/htcn/research/outcome_evaluator.py`
3. `src/htcn/research/outcome_snapshot.py`
4. `src/htcn/research/outcome_engine_identity.py`

exact code anchor：

`9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8`

`m4_outcome_engine_freeze_guard.py` 在私有 M1 update 之前验证：

- engine contract version = 1；
- component count = 4；
- frozen anchor 是 HEAD ancestor；
- 4 个 component 全部存在；
- `git diff 9cbc0d3d... HEAD -- <4 paths>` 为空；
- active outcome protocol = v2；
- v2 protocol JSON 通过 canonical fingerprint validator。

任一失败：

- 不更新私有 M1；
- 不产生新 authoritative capture；
- 不产生新 outcome snapshot。

---

## 10. Bundle / intake independent verification

Evidence bundle 包含：

- frozen capture baseline + committed transactions；
- active outcome protocol v2 JSON；
- historical v1 protocol JSON（如存在）；
- outcome engine freeze-guard report；
- outcome snapshots；
- outcome report；
- transition / observation / health reports。

权威层次：

- enrollment authority：
  frozen baseline + immutable committed captures；
- outcome evidence：
  separate immutable outcome snapshots；
- bundle：
  transport only。

Intake 不相信 derived report。

它必须：

1. 重新验证 capture authority；
2. 重建 prospective cohort；
3. 验证 bundled protocol；
4. 验证 outcome snapshot schema / hash / chain identity；
5. 从 snapshot 的 OHLCV path 离线重跑 evaluator；
6. 对 stored result 与 recomputed result 逐 candidate 比较。

即使攻击者：

- 修改 Source Terminal / Type-I / MFE；
- 重新生成 snapshot ID；
- 重新生成 ZIP manifest SHA；

只要 semantic result 与 frozen evaluator 不一致，intake 仍必须报：

`outcome_result_recompute_drift`

---

## 11. One-click workflow

唯一私有 M1 入口仍是：

`运行M4真实A股生命周期快照.bat`

Phase 3.1 顺序：

1. branch / minimum-safe / clean-worktree preflight；
2. capture methodology exact-freeze guard；
3. outcome engine exact-freeze guard；
4. M1 smart daily update；
5. authoritative lifecycle capture；
6. evidence health；
7. transition report；
8. prospective observation report；
9. outcome-v2 report / immutable snapshot；
10. handoff bundle。

Outcome stage 只在 capture / health / observation 通过后执行。

没有 outcome cohort：

`no_outcome_cohort`

是正常状态，不是假失败，也不允许为了“出统计”放宽 cohort。

Phase 3.1 minimum-safe workflow checkpoint：

`c34026755b3b8c491759eaacdb45376d4e1db485`

---

## 12. 明确禁止

Outcome v2 不定义：

- trade entry；
- stop-loss；
- position size；
- fees；
- execution P&L；
- win/loss label；
- win rate；
- alpha；
- benchmark excess return；
- p-value；
- significance；
- buy/sell ranking。

因此：

`alpha_inference_allowed=false`

`is_trade_instruction=false`

Phase 3.1 完成也**不等于策略盈利验证完成**。

---

## 13. 第一笔真实 outcome 前状态

截至本 spec 冻结：

- T0 = 2026-09-17 legacy baseline inventory；
- T0 candidate = 87；
- T0 prospective outcome eligible = 0；
- 尚无 post-T0 real authoritative future capture；
- 尚无真实 prospective-new outcome cohort；
- 尚无真实 outcome snapshot；
- 尚无真实 MFE/MAE prospective result。

因此 v1→v2、snapshot schema v2、engine identity 与离线复算都发生在第一笔真实 prospective outcome 之前，不涉及事后看样本改口径。
