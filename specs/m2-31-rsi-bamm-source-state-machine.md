# M2.31 — RSI BAMM Dedicated Source State Machine

## Status

**Phase 4 frozen.** Phase 3 indicator sequencing and Phase 4 Source Terminal Price Bar lifecycle integration are accepted. GitHub Actions run #643 / `35209013814` passed deterministic Python tests, Web build, Playwright smoke/lifecycle acceptance, the frozen 45-symbol A-share source-PRZ v6 research chain, RSI BAMM observability, and the existing Type-I holdout/external-replication guards.

## Why this Gate exists

The legacy lifecycle Wilder RSI 30/70 audit remains explicitly **not RSI BAMM**. Carney RSI BAMM is a staged indicator/price confirmation process. It is confirmation/execution evidence and must never create harmonic identity or mutate Source Raw PRZ.

## Source contract

### Common requirements

- Wilder RSI period: 14.
- Bullish extreme zone: below 30.
- Bearish extreme zone: above 70.
- Two distinct extreme tests are required.
- The tests must be separated by a minimum reaction to RSI 50.
- The secondary test is impulsive.
- BAMM does not mutate harmonic identity or Source Raw PRZ.

### Four Volume Three profiles

1. **Simple Confirmation** — initial impulse + midpoint reaction + secondary impulse; price and RSI confirm in the reversal direction.
2. **Complex Confirmation** — initial complex W/M + midpoint reaction + secondary impulse; price and RSI confirm in the reversal direction.
3. **Simple Divergence** — two impulses separated by midpoint reaction; price makes a nominal new trend extreme while RSI fails to confirm it.
4. **Complex Divergence** — initial complex W/M + midpoint reaction + secondary impulse; price makes a nominal new trend extreme while RSI diverges.

Bullish confirmation = price higher / RSI higher; bullish divergence = price lower / RSI higher.
Bearish confirmation = price lower / RSI lower; bearish divergence = price higher / RSI lower.

## Volume Two seven-step complex workflow

1. initial extreme test;
2. complete W-type bullish / M-type bearish complex RSI structure inside the extreme zone;
3. Trigger Bar = bar that completes the complex structure by exiting 30/70;
4. RSI/price reaction;
5. final divergence only after mandatory RSI 50 midpoint reaction;
6. Confirmation Point uses 1.13 or 1.618 based on Trigger Bar location relative to prior price extreme;
7. coordinate Confirmation Point with a distinct harmonic-pattern completion.

Ratio selection:

- Trigger Bar at prior price extreme => 1.618;
- Trigger Bar away from prior price extreme => 1.13.

## X-A price projection freeze

HT-CN freezes:

- `X` = prior price extreme associated with first RSI structure;
- `A` = most favorable price extreme of the initial reaction after Trigger Bar and before secondary extreme test starts;
- target = `A + ratio * (X - A)`.

A is frozen before the secondary extreme begins. If X-A has no valid directional span, projection remains unresolved and source confirmation fails closed.

## Phase 4 Source Terminal Price Bar confluence

Phase 3 `confirm_rsi_bamm_with_match()` remains a geometry-terminal compatibility/golden-test adapter. It is **not** the production lifecycle clock.

Phase 4 production/lifecycle confirmation uses:

- `observe_source_execution_for_match(frame, match)` to reconstruct the observable source execution clock from the pre-terminal pivot confirmation;
- `confirm_rsi_bamm_with_source_execution(sequence, match, audit)` to bind BAMM to the resulting Source Terminal Price Bar.

The source-clock adapter hard-gates:

1. 5-0 remains rejected while production quarantine is active;
2. match and evaluation must be completed;
3. BAMM direction and harmonic direction must agree;
4. a frozen Source Raw PRZ must exist;
5. the source execution audit must refer to the same Source Raw PRZ and direction;
6. an observable Source Terminal Price Bar must actually have been established before or at the historical terminal pivot;
7. the Source T-Bar must occur during the secondary impulsive RSI extreme-test window;
8. only then may the lower-level BAMM combiner receive a completed-harmonic assertion.

### Geometry terminal is not Source T-Bar

A right-confirmed historical D/C pivot is diagnostic geometry. It must not be silently relabeled as the execution Terminal Price Bar.

For a completed historical match, Phase 4 reconstructs observability from:

`pre-terminal pivot index + scale -> source PRZ entry -> Source Terminal Price Bar`

and caps the reconstruction at the historical terminal-pivot bar so a later unrelated PRZ touch cannot be attached retroactively.

### PEZ overspill

Volume Three PEZ integrates the static Source Raw PRZ with the observed Terminal Bar extreme. Therefore a valid T-Bar may penetrate beyond the terminal harmonic number. Phase 4 requires a valid terminal-side test of the same source zone; it does **not** require the T-Bar extreme to remain inside the static Raw PRZ interval.

Static interval membership remains diagnostic. PEZ overspill does not mutate Source Raw PRZ.

## 1.13 retracement-pattern precedence

Volume Two documents retracement-pattern completion that can precede the minimum 1.13 BAMM projection. HT-CN restricts this exception to source-cleared XABCD `gartley` and `bat`, selected 1.13 BAMM projection only, and the correct directional relationship. No generic ATR, percentage, tick, or PRZ-distance tolerance is invented.

## Dedicated pattern boundaries

- Standalone AB=CD uses the M2.28 Source Raw PRZ resolver.
- Shark uses the M2.30 Source Raw PRZ and is not eligible for the Gartley/Bat 1.13 precedence exception.
- 5-0 remains production quarantined even though its Volume Two structural PRZ is frozen.
- Alternate Bat remains source-conflict fail closed.

## Engineering classifier boundary

Carney describes complex W/M structures qualitatively but does not publish a deterministic bar-by-bar RSI pivot algorithm. HT-CN operationalizes complex extreme structure conservatively. This classifier is engineering logic and cannot alter pattern identity, PRZ, or historical frozen research.

## No-lookahead contract

- classify an extreme structure only at the 30/70 exit;
- record midpoint only when RSI actually reaches 50 after the first structure;
- a retest before midpoint cannot be rescued by later data;
- freeze X-A reaction anchor before secondary extreme entry;
- emit sequence only on secondary extreme exit;
- future bars cannot change completion timestamp or projection anchors;
- reconstruct completed-match Source T-Bar only from a pre-terminal projection that was observable before the historical terminal pivot;
- evidence becomes usable at `max(Source T-Bar, BAMM sequence completion)` and is never backdated.

## Lifecycle evidence channels

- `forming[].execution_clock.rsi_bamm_evidence`: BAMM visibility at/after an observed source execution clock.
- `completed[].rsi_bamm_evidence`: source-terminal-bound harmonic confluence.

Both channels are evidence only. Neither may mutate harmonic identity or Source Raw PRZ.

## Frozen 45-symbol A-share observability

Dataset: `a-share-research-v2-45`, snapshot cutoff `2026-09-15`.

Run #643 / `35209013814` on validated commit `0c7799391bc92af46a2b249892dc24e06a6143a0`:

- successful symbols: 45 / 45; failures: 0;
- RSI BAMM sequences: 686;
- profile counts: Complex Confirmation 151, Complex Divergence 100, Simple Confirmation 253, Simple Divergence 182;
- relation counts: Confirmation 404, Divergence 282;
- completed source-scannable harmonic matches: 174;
- source-clock observable matches: 128;
- source terminal observed matches: 23;
- source execution states: awaiting PRZ entry 26, PRZ entered waiting terminal 79, terminal observed 23, unavailable 46;
- strict source-confirmed BAMM/harmonic confluences: 2, both standalone AB=CD;
- evidence available at Source T-Bar: 1;
- evidence available only after BAMM completion: 1.

These numbers are **observability only**. They do not estimate hit rate, profitability, alpha, expectancy, or current-stock probabilities and cannot be used to tune identity, Source Raw PRZ, or thresholds.

## Acceptance status

- [x] four Volume Three profile families covered by regression;
- [x] mandatory midpoint negative regression;
- [x] complex-secondary negative regression;
- [x] prefix/no-lookahead regression;
- [x] 1.13 vs 1.618 ratio-selection regression;
- [x] X-A projection math and unresolved-projection fail-closed regression;
- [x] Phase-3 geometry-terminal compatibility regressions;
- [x] standalone AB=CD / Shark / 5-0 quarantine regressions;
- [x] source execution clock reconstruction regression;
- [x] Source T-Bar distinct from historical D/C regression;
- [x] valid PEZ overspill regression;
- [x] lifecycle evidence no-backdating regression;
- [x] Source Truth drift guard;
- [x] final deterministic/browser CI;
- [x] frozen 45-symbol source-clock BAMM observability;
- [x] existing Type-I holdout/external-replication guards unchanged and green.

## Next mainline gate

**M3 Source-Clock Lifecycle Migration.**

The workbench must migrate from retrospective D-clock overlays to the observable Source Terminal Price Bar / PEZ / T+1 / Type-I / Type-II state model. BAMM appears as a separate evidence channel and must not become a pattern-identity switch. The optional BAMM Acceleration Trigger remains deferred until after this migration is frozen.
