# M2.31 — RSI BAMM Dedicated Source State Machine

## Status

**Phase 2 active.** Indicator sequencing and X-A Confirmation Point projection are now implemented. Direct integration with harmonic pattern objects/workbench remains gated until adapter tests are added.

## Why this Gate exists

The existing HT-CN lifecycle code contains only a lightweight Wilder RSI 30/70 reversal audit and explicitly labels it `indicator_evidence_is_rsi_bamm=False`. That separation remains correct.

Carney RSI BAMM is not a synonym for oversold/overbought. Volume Two defines a multi-stage process; Volume Three distinguishes four structural types. M2.31 therefore owns a dedicated no-lookahead state machine.

## Source contract

### Common requirements

- Wilder RSI period: 14.
- Bullish extreme zone: below 30.
- Bearish extreme zone: above 70.
- Two distinct extreme tests are required.
- The tests must be separated by a minimum reaction to RSI 50.
- The secondary test is impulsive.
- BAMM is confirmation/execution evidence; it does not mutate harmonic identity or Source Raw PRZ.

### Four Volume Three profiles

1. **Simple Confirmation** — initial impulse + midpoint reaction + secondary impulse; price and RSI confirm in the same reversal direction.
2. **Complex Confirmation** — initial complex W/M + midpoint reaction + secondary impulse; price and RSI confirm in the same reversal direction.
3. **Simple Divergence** — two impulses separated by midpoint reaction; price makes a nominal new trend extreme while RSI fails to confirm it.
4. **Complex Divergence** — initial complex W/M + midpoint reaction + secondary impulse; price makes a nominal new trend extreme while RSI diverges.

Bullish: confirmation = price higher / RSI higher; divergence = price lower / RSI higher.

Bearish: confirmation = price lower / RSI lower; divergence = price higher / RSI lower.

## Volume Two seven-step complex workflow

1. initial extreme test;
2. complete W-type bullish / M-type bearish complex RSI structure inside the extreme zone;
3. Trigger Bar = bar that completes the complex structure by exiting 30/70;
4. RSI/price reaction;
5. final divergence only after mandatory RSI 50 midpoint reaction;
6. Confirmation Point uses 1.13 or 1.618 based on Trigger Bar location relative to prior price extreme;
7. coordinate Confirmation Point with distinct harmonic-pattern completion.

Ratio selection:

- Trigger Bar at prior price extreme => 1.618;
- Trigger Bar away from prior price extreme => 1.13.

## X-A price projection freeze

Volume Two explicitly describes the bearish final spillover as a 1.13/1.618 extension of the initial breakdown `X-A`; bullish figures use the mirrored initial reaction.

HT-CN v2 freezes:

- `X` = prior price extreme associated with first RSI structure;
- `A` = most favorable price extreme of the initial reaction after Trigger Bar and before secondary extreme test starts;
- target = `A + ratio * (X - A)`.

This is the standard external extension from A back through X. It produces the book's intended nominal new low/high rather than incorrectly projecting another full leg outward from X.

No-lookahead: A is frozen before the secondary extreme begins; later bars cannot move X or A for an already-emitted sequence.

If X-A has no valid directional span, projection remains unresolved and final source confirmation fails closed.

## Harmonic-pattern coordination and 1.13 exception

Normal source confirmation requires:

- complete BAMM indicator sequence;
- X-A Confirmation Point tested;
- distinct harmonic pattern completed in coordination with the final RSI retest.

Volume Two also documents a 1.13-side retracement-pattern exception: a distinct retracement harmonic pattern may complete before the minimum 1.13 extension and take precedence. HT-CN exposes this only as an explicit adapter flag and only when the selected BAMM ratio is 1.13. It is not a generic bypass.

The next phase must bind this flag to actual source-cleared harmonic pattern objects rather than caller assertion.

## Engineering classifier boundary

Carney describes complex W/M structures qualitatively but does not publish a deterministic bar-by-bar RSI pivot algorithm. HT-CN operationalizes a complex extreme structure conservatively:

- all constituent RSI observations remain in the extreme zone until exit;
- bullish requires an internal recovery followed by a second decline before exiting above 30;
- bearish requires an internal pullback followed by a second rise before exiting below 70.

This classifier is engineering logic and cannot alter harmonic pattern identity, PRZ or historical frozen research.

## No-lookahead contract

- extreme structure classified only at 30/70 exit;
- midpoint recorded only when RSI actually reaches 50 after first structure;
- a retest before midpoint cannot be rescued by later data;
- X-A reaction anchor is frozen before secondary extreme entry;
- sequence emitted only on secondary extreme exit;
- future bars cannot change completion timestamp or projection anchors.

## Acceptance status

- [x] bullish Simple Confirmation regression;
- [x] bullish Simple Divergence regression;
- [x] bullish Complex Divergence regression;
- [x] bearish mirrored Confirmation and Divergence regressions;
- [x] missing-midpoint negative regression;
- [x] complex-secondary negative regression;
- [x] prefix/no-lookahead regression;
- [x] 1.13 vs 1.618 ratio-selection regression;
- [x] bullish and bearish X-A projection math regression;
- [x] unresolved projection fail-closed regression;
- [x] 1.13 retracement-pattern precedence regression;
- [x] existing lifecycle Wilder RSI evidence remains explicitly non-BAMM.

## Next Phase

1. bind `harmonic_pattern_completed` and the 1.13 retracement exception to real source-cleared HT-CN harmonic match objects;
2. expose BAMM as a separate evidence channel on the source-aligned Terminal Price Bar / lifecycle layer without rewriting identity;
3. add real A-share BAMM observability report with no outcome fitting;
4. evaluate optional Acceleration Trigger only after core BAMM adapter is frozen.
