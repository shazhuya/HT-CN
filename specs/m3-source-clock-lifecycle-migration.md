# M3 — Source-Clock Lifecycle Migration

## Status

**Phase 1 lifecycle implemented; Phase 2 chart migration implemented; Phase 3 A-share execution context implemented and under acceptance.** M2.31 Source Fidelity is frozen on `main`. M3 migrates the product-facing lifecycle away from retrospective D/C geometry and onto the observable Source Terminal Price Bar execution clock, makes that clock visually explicit, then surrounds it with a separate A-share tradability/volatility layer.

## Why this migration exists

M2.31 proved that historical completed geometry and live execution observability are not equivalent. On the frozen 45-symbol A-share sample, 174 historical completed source-scannable matches produced only 128 reconstructable pre-terminal source clocks and 23 observed Source Terminal Price Bars. Therefore a workbench that labels the current state from historical D/C is structurally capable of showing states that were not observable at the time.

The M3 product contract is therefore:

> **current state comes from the source execution clock; historical reaction audit is diagnostic compatibility only.**

## Canonical state chain

Phase 1 freezes the following product state vocabulary:

1. `source_clock_unavailable`
2. `source_prz_unresolved`
3. `approaching_source_prz`
4. `entered_source_prz`
5. `waiting_terminal`
6. `source_terminal_complete`
7. `t_plus_1`
8. `type_i_early_reaction`
9. `type_i_confirmed`
10. `type_i_failed`
11. `reaction_only`
12. `type_ii_retest_forming`
13. `type_ii_terminal`
14. `reversal_evidence`
15. `invalidated` — vocabulary reserved; current M3 work does not invent a new source invalidation rule merely to emit it.

## Clock ownership

### Geometry clock

Historical/right-confirmed D/C points remain useful for geometry audit, pattern drawing, retrospective quality research and compatibility reports. They do **not** own the live/current lifecycle.

### Source execution clock

Canonical current-state inputs are:

`observable forming signal -> frozen Source Raw PRZ -> first PRZ entry -> Source Terminal Price Bar -> PEZ -> T-Bar+1 -> post-terminal price path`

For completed historical matches, the Source T-Bar must first be reconstructed from the pre-terminal observable projection using the M2.31 canonical helper. A later unrelated PRZ touch cannot be attached retroactively.

## Phase 1 Type-I operational states

Carney Volume Three emphasizes a demonstrative early Type-I reaction and the importance of the first roughly 3–5 bars after the Terminal Price Bar. HT-CN Phase 1 therefore uses a product/execution operationalization that does **not** alter pattern identity:

- `t_plus_1`: first bar after Source T-Bar;
- `type_i_early_reaction`: still within the first five bars and 38.2% reaction objective not yet reached;
- `type_i_confirmed`: 38.2% objective reached no later than T-Bar+5;
- `type_i_failed`: first five bars ended without reaching 38.2%;
- `reaction_only`: 38.2% reached only after the five-bar early window.

These labels are execution-state semantics, not source identity rules and not profitability claims. They do not modify Source Raw PRZ or retroactively change the harmonic match.

## Phase 1 Type-II operational states

Production keeps the existing conservative HT-CN strict policy:

1. price must first exit Source Raw PRZ in the reversal direction;
2. price then re-enters the same frozen Source Raw PRZ;
3. partial overlap emits `type_ii_retest_forming` only;
4. only a terminal-side/full source-zone retest emits `type_ii_terminal`;
5. a subsequent reversal-direction exit emits `reversal_evidence`.

This is the HT-CN strict production operationalization of Carney's ideal full-retest case. It is not a claim that Carney rejects every nominal-retest case.

## Evidence channels do not own lifecycle

The following may be displayed next to lifecycle state but cannot set or repair that state: RSI BAMM, ordinary Wilder RSI evidence, geometry score, A-share index/sector context, ATR/liquidity/T+1 tradability and research statistics.

RSI BAMM remains M2.31 evidence-only. A `source_confirmed` BAMM badge can strengthen interpretation, but the lifecycle state still comes from Source T-Bar and subsequent price path.

## Product questions

Every canonical state should answer, in Chinese-first language:

- **现在在哪** — current source-clock state;
- **先看哪** — first evidence/price event to observe;
- **到了再看哪** — next lifecycle transition;
- **当前动作** — wait/observe/enter the next execution assessment layer, without issuing trades;
- **下一关键价位** — only when that price is derivable from frozen Source PRZ / PEZ / 38.2 / 61.8 management levels.

## API contract

M3 adds `source_lifecycle` on individual pattern payloads and top-level `source_lifecycle_contract`.

Canonical fields include current `state` and `state_reason`, source signal/entry/Terminal/T+1 timestamps, bars since Terminal, T1/T2 observation bars, first reversal-direction Source PRZ exit, Type-II re-entry/terminal/post-terminal exit bars, Source PRZ/PEZ/T1/T2 prices, next key price and semantic role, and `retrospective_geometry_clock_used=false`.

The service adapter is intentionally layered on top of the frozen M2.31 source-aligned service so M3 product migration cannot silently rewrite M2 identity/PRZ code.

## No-lookahead acceptance

Phase 1 must prove by prefix regression that later states never appear in earlier data prefixes. The required transition regression covers:

`approaching -> entered -> waiting terminal -> Source T-Bar -> T+1 -> Type-I confirmed -> Type-II retest forming -> Type-II terminal -> reversal evidence`

Additional guards require:

- unresolved Source PRZ fails closed;
- Type-I early failure is not pattern identity invalidation;
- a late 38.2% reaction cannot be backdated into early Type-I confirmation;
- unreconstructable completed source clocks remain `source_clock_unavailable` instead of falling back to D/C;
- front-end canonical state overrides contradictory retrospective audit;
- BAMM renders as a separate evidence channel.

A targeted independent prefix validation of the canonical transition chain has also been run outside GitHub Actions while the hosted runner is unavailable; the expected sequence passed through all states without future-state backfill. This targeted check supplements but does not replace the repository CI gate.

## Phase 1 acceptance checklist

- [x] canonical source lifecycle enum/payload implemented;
- [x] prefix-safe state derivation implemented;
- [x] completed-match adapter uses reconstructed Source T-Bar;
- [x] forming execution clock promoted to canonical source lifecycle;
- [x] API switched to M3 source-clock adapter;
- [x] Chinese-first LifecycleCompass prefers canonical lifecycle over retrospective audit;
- [x] separate BAMM evidence channel in workbench;
- [x] deterministic no-lookahead regressions added;
- [x] Playwright contradictory-clock and BAMM-channel regressions added;
- [x] targeted independent prefix transition validation passed;
- [ ] GitHub-hosted CI Python tests observed running and green;
- [ ] GitHub-hosted Web build observed running and green;
- [ ] GitHub-hosted Playwright observed running and green.

The remaining unchecked items are currently blocked by a repository/GitHub-hosted runner scheduling failure in which jobs terminate before runner allocation (`runner_id=0`, zero steps, no log blob). M3 development must not wait idle on this infrastructure condition.

## Phase 2 — Source lifecycle chart migration

Phase 2 makes the source clock visible on the K-line chart instead of leaving it only in text cards.

### Visual layers

When `source_lifecycle` is available, the chart now treats the following as canonical execution overlays:

- **Source Raw PRZ** — drawn from the observable source signal forward;
- **PEZ** — drawn only after Source Terminal Price Bar exists; valid terminal overspill is visually preserved rather than forcing the T-Bar back inside static Raw PRZ;
- **Source T-Bar** — vertical event line + price node;
- **T-Bar+1** — explicit execution-start event;
- **Source Type-I 38.2 / 61.8 targets** — sourced from the source execution clock, not retrospective D targets;
- **Type-II re-entry** — first secondary Source PRZ re-entry after reversal-direction exit;
- **Type-II Terminal** — strict full/terminal-side retest event;
- **Type-II post-terminal reversal-direction exit** — explicit price confirmation event.

Historical HT-CN ideal-core/legacy PRZ and retrospective targets remain diagnostic fallback only. When source lifecycle exists, the target overlay is tagged `data-clock="source"`; retrospective target overlays are visually de-emphasized.

### Browser protection

Phase 2 adds browser acceptance asserting that a source lifecycle scenario visibly contains Source PRZ, PEZ, Source T-Bar, T+1 and Source Type-I event/target layers. This protects against a future UI regression that accidentally restores D-clock overlays as the primary chart narrative.

### Phase 2 acceptance checklist

- [x] Source Raw PRZ overlay implemented;
- [x] PEZ overlay implemented;
- [x] Source T-Bar and T+1 event markers implemented;
- [x] Source Type-I 38.2/61.8 target overlays implemented;
- [x] Type-II re-entry / Terminal / post-terminal exit marker support implemented;
- [x] source-vs-retrospective target provenance exposed in DOM;
- [x] local TypeScript syntax/type shape check for HarmonicChart passed;
- [x] Playwright source-overlay regression added;
- [ ] full Web build observed green in repository CI;
- [ ] Playwright screenshot/browser artifact observed green in repository CI.

## Phase 3 — A-share execution/tradability context

Phase 3 surrounds the canonical source lifecycle with A-share execution constraints without allowing those constraints to own or mutate harmonic semantics.

### Backend contract

`a_share_execution_context` is emitted at analysis level and copied onto pattern payloads for workbench rendering. It contains auditable raw fields rather than a composite score:

- board / security metadata availability / listing date / ST status;
- `t_plus_one=true` and same-day sell-after-buy disabled for ordinary A shares;
- board nominal price-limit percentage;
- `rule_based_price_limit_pct` only when board / risk-warning / listing-age metadata is sufficient;
- explicit `price_limit_status` and `special_event_exceptions_unresolved`;
- IPO first-five-trading-session state;
- Wilder ATR(14), ATR%, latest high-low range normalized by prior close;
- prior-20-session average volume and current volume ratio;
- BSE deferred;
- hard `mutates_harmonic_identity=false` and `mutates_source_raw_prz=false`.

### Price-limit truth boundary

The code intentionally does **not** expose an `exact_price_limit_pct` field. Even when board/listing/ST metadata resolves the normal rule profile, suspension/resumption and special-security events require richer event metadata. Therefore:

- `nominal_price_limit_pct` = ordinary board rule;
- `rule_based_price_limit_pct` = rule profile after known listing-age/ST/date adjustments;
- `special_event_exceptions_unresolved=true` = do not present that value as the exact daily limit price.

Current date-aware contract includes the 2026-07-06 main-board risk-warning transition and the first-five-listing-session no-daily-limit exception. Missing metadata fails safe rather than guessing.

### UI contract

The Workbench renders a separate **A 股执行约束与波动背景** card before the lifecycle navigator. It shows T+1, rule-based price-limit context, ATR%, current range, 20-session volume context and metadata completeness. The note explicitly states that the card cannot create, repair or reject harmonic identity or Source Raw PRZ.

### Phase 3 acceptance checklist

- [x] standalone `a_share_execution_context` backend module implemented;
- [x] security metadata loader is lazy and fail-safe;
- [x] M3 service attaches execution context without changing M2.31 objects;
- [x] date-gated main-board risk-warning 2026-07-06 regression added;
- [x] STAR/ChiNext 20% board-rule regression added;
- [x] IPO first-five-session no-daily-limit regression added;
- [x] missing-metadata fail-safe regression added;
- [x] ATR / ATR% / range / volume-ratio fields implemented;
- [x] black-box composite execution score deliberately omitted;
- [x] execution-context Workbench card implemented;
- [x] targeted TypeScript check for the execution-context card passed outside GitHub Actions;
- [ ] real local catalog metadata read smoke-tested on a populated M1 database;
- [ ] full Python suite observed green after Phase 3 changes;
- [ ] full Web build / Playwright observed green after Phase 3 changes.

## Not in the current migration batch

- no new pattern family;
- no relaxation of Alternate Bat fail-closed;
- no removal of 5-0 quarantine;
- no BAMM Acceleration Trigger;
- no nominal Type-II production tier;
- no A-share execution scoring/ranking;
- no claim of stable alpha;
- no invented source invalidation rule merely to populate `invalidated`;
- no claim that `rule_based_price_limit_pct` equals the exact daily limit under unresolved special events.

## Next gate

The next gate is **M3 Phase 3.1 — real metadata/tradability hardening**:

1. smoke-test `security_master` integration on a populated M1 catalog;
2. add event metadata needed to resolve suspension/resumption and other price-limit exceptions instead of guessing;
3. add browser regression for the execution-context card;
4. once GitHub-hosted runners recover, run the full Python/Web/Playwright gate without changing semantics merely to make CI green.

Only after those checks should M3 move toward market/sector context, ranking or user-facing decision prioritization.
