# M2.31 — RSI BAMM Dedicated Source State Machine

## Status

**Phase 3 frozen.** Indicator sequencing, X-A Confirmation Point projection, and binding to real source-cleared harmonic matches are implemented. The next phase is lifecycle/Terminal Price Bar evidence-channel integration plus real A-share observability; it must not rewrite identity or Source Raw PRZ.

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

## Real harmonic confluence adapter freeze

Canonical source confirmation now uses `confirm_rsi_bamm_with_match(sequence, match)`. Callers cannot obtain a source-confirmed claim by passing `harmonic_pattern_completed=True` directly through the canonical integration path.

The adapter hard-gates, in order:

1. 5-0 is rejected while its production quarantine remains active;
2. the match and its evaluation must both be `COMPLETED`;
3. BAMM direction and harmonic direction must agree;
4. the harmonic object must expose a frozen Source Raw PRZ;
5. its terminal price must lie inside that Source Raw PRZ;
6. its terminal bar must fall inside the secondary impulsive RSI extreme-test window;
7. only then may the lower-level BAMM combiner receive a completed-harmonic assertion.

Standalone AB=CD uses the M2.28 source resolver. Its Raw PRZ deliberately preserves equivalent AB=CD and reciprocal-BC measurements, so a narrow interval is valid and must not be collapsed into an artificial point.

Shark uses the M2.30 Source Raw PRZ contract. Shark is not eligible for the Volume Two 1.13 retracement-pattern precedence exception.

### 1.13 retracement-pattern precedence

Volume Two explicitly documents a retracement-pattern completion that can precede the minimum 1.13 BAMM projection. HT-CN restricts this exception to source-cleared XABCD `gartley` and `bat` matches, selected 1.13 BAMM projection only, and a terminal price that genuinely precedes the projection in the correct directional sense.

No generic percentage, ATR, tick or PRZ-distance tolerance is invented. If the source relationship is not demonstrated by the frozen objects, confirmation fails closed.

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
- future bars cannot change completion timestamp or projection anchors;
- harmonic confluence uses an already-completed source-cleared match and never backdates the BAMM sequence.

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
- [x] real completed XABCD confluence regression;
- [x] direction-mismatch and temporal-window negative regressions;
- [x] unresolved Source Raw PRZ negative regression;
- [x] standalone AB=CD M2.28 Source Raw PRZ regression;
- [x] Shark source completion regression;
- [x] 5-0 production-quarantine regression;
- [x] 1.13 Gartley/Bat precedence is object-bound rather than caller-asserted;
- [x] existing lifecycle Wilder RSI evidence remains explicitly non-BAMM.

## Next Phase

1. expose source-confirmed BAMM as a separate evidence channel on source-aligned Terminal Price Bar / lifecycle objects without rewriting identity;
2. add real A-share BAMM observability report with no outcome fitting and no new research-version relabel;
3. add lifecycle temporal/no-lookahead regressions for that evidence channel;
4. evaluate optional Acceleration Trigger only after the core lifecycle integration is frozen.
