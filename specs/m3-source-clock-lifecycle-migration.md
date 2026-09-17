# M3 Phase 1 — Source-Clock Lifecycle Migration

## Status

**Implementation candidate.** M2.31 Source Fidelity is frozen on `main`. M3 Phase 1 migrates the product-facing current lifecycle away from retrospective D/C geometry and onto the observable Source Terminal Price Bar execution clock.

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
15. `invalidated` — vocabulary reserved; Phase 1 does not invent a new source invalidation rule merely to emit it.

## Clock ownership

### Geometry clock

Historical/right-confirmed D/C points remain useful for:

- geometry audit;
- pattern drawing;
- retrospective quality research;
- compatibility reports.

They do **not** own the live/current lifecycle.

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

The following may be displayed next to lifecycle state but cannot set or repair that state:

- RSI BAMM;
- ordinary Wilder RSI evidence;
- geometry score;
- A-share index/sector context;
- ATR / liquidity / T+1 tradability;
- research statistics.

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

Canonical fields include:

- current `state` and `state_reason`;
- source signal / entry / Terminal / T+1 timestamps;
- bars since Terminal;
- T1/T2 observation bars;
- first reversal-direction Source PRZ exit;
- Type-II re-entry / terminal / post-terminal exit bars;
- Source PRZ / PEZ / T1 / T2 prices;
- next key price and semantic role;
- `retrospective_geometry_clock_used=false`.

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
- [ ] CI Python tests pass on M3 branch;
- [ ] Web build passes on M3 branch;
- [ ] Playwright lifecycle/smoke pass on M3 branch;

## Not in Phase 1

- no new pattern family;
- no relaxation of Alternate Bat fail-closed;
- no removal of 5-0 quarantine;
- no BAMM Acceleration Trigger;
- no nominal Type-II production tier;
- no A-share execution scoring/ranking;
- no claim of stable alpha;
- no invented source invalidation rule merely to populate `invalidated`.

## Next after Phase 1

After deterministic/browser acceptance, Phase 2 will migrate chart overlays and detailed workbench price markers from retrospective T1/T2 labels toward Source PRZ / PEZ / Source T-Bar / T+1 / live Type-I/II markers, while retaining historical geometry as a visually distinct diagnostic layer.
