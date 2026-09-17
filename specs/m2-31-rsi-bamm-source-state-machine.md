# M2.31 — RSI BAMM Dedicated Source State Machine

## Status

**Phase 1 active.** This spec freezes the indicator-sequence contract first. Exact X-A price projection coordinates remain fail-closed until a separate figure-level source audit resolves them.

## Why this Gate exists

The existing HT-CN lifecycle code contains only a lightweight Wilder RSI 30/70 reversal audit and explicitly labels it `indicator_evidence_is_rsi_bamm=False`. That separation is correct and must remain.

Carney RSI BAMM is not a synonym for oversold/overbought. Volume Two describes a multi-stage process; Volume Three further distinguishes four structural types. Therefore M2.31 creates a dedicated state machine rather than renaming the existing RSI evidence.

## Source contract

### Common requirements

- Wilder RSI period: 14.
- Bullish extreme zone: below 30.
- Bearish extreme zone: above 70.
- Two distinct extreme tests are required.
- The tests must be separated by a minimum reaction to the RSI 50 midpoint.
- The secondary test is impulsive.
- BAMM remains confirmation/execution evidence; it does not mutate harmonic identity or Source Raw PRZ.

Volume Three makes the 50 midpoint reaction an absolute structural separator across all four BAMM types.

### Four Volume Three profiles

1. **Simple Confirmation** — initial impulse + midpoint reaction + secondary impulse; price and RSI confirm in the same reversal direction.
2. **Complex Confirmation** — initial complex W/M + midpoint reaction + secondary impulse; price and RSI confirm in the same reversal direction.
3. **Simple Divergence** — two impulses separated by midpoint reaction; price makes a nominal new trend extreme while RSI fails to confirm it.
4. **Complex Divergence** — initial complex W/M + midpoint reaction + secondary impulse; price makes a nominal new trend extreme while RSI diverges.

Bullish relation:

- confirmation: second price low higher AND second RSI low higher;
- divergence: second price low lower AND second RSI low higher.

Bearish relation:

- confirmation: second price high lower AND second RSI high lower;
- divergence: second price high higher AND second RSI high lower.

## Volume Two seven-step complex workflow

The strict complex workflow remains explicit:

1. initial extreme test;
2. complete W-type bullish / M-type bearish complex RSI structure inside the extreme zone;
3. Trigger Bar = bar that completes the complex structure by exiting 30/70;
4. RSI/price reaction;
5. final divergence only after the mandatory RSI 50 midpoint reaction;
6. Confirmation Point selects 1.13 or 1.618 based on Trigger Bar location relative to the prior price extreme;
7. coordinate the Confirmation Point with distinct harmonic-pattern completion.

Ratio selection frozen in Phase 1:

- Trigger Bar is the prior price extreme => 1.618;
- Trigger Bar is not the prior price extreme => 1.13 (the primary examples commonly show a few-bar offset).

## Explicit unresolved item

The books clearly show and discuss X-A / prior-initial-reaction extensions, but Phase 1 does **not** yet encode an exact target-price formula because the figure anchors must be reconciled across bullish, bearish, simple/complex, and retracement-pattern exceptions.

Therefore:

- the state machine emits `confirmation_extension_ratio`;
- it does **not** emit an invented target price;
- `price_projection_resolved=False`;
- final `source_confirmed` status is blocked even if a caller passes `price_confirmation_tested=True` and `harmonic_pattern_completed=True`.

This is intentional fail-closed source governance.

## Engineering classifier boundary

Carney describes complex W/M structures qualitatively but does not publish a deterministic bar-by-bar RSI pivot algorithm. HT-CN v1 operationalizes a complex extreme structure conservatively:

- every observation remains inside the relevant extreme zone until the exit bar;
- bullish requires an internal recovery followed by a second decline before exiting above 30;
- bearish requires an internal pullback followed by a second rise before exiting below 70.

This classifier is tagged as engineering operationalization. It cannot alter Carney pattern identity, PRZ or research labels outside BAMM itself.

## No-lookahead contract

- an extreme structure is not classified until its 30/70 exit bar is observed;
- midpoint evidence is recorded only when RSI actually reaches 50 after the first structure;
- the second test cannot pair with the first if it occurs before midpoint evidence;
- the sequence is emitted only on the second extreme-zone exit bar;
- future bars cannot retroactively create an earlier BAMM completion timestamp.

## Phase 1 acceptance

- [ ] bullish Simple Confirmation Book Golden synthetic regression;
- [ ] bullish Simple Divergence regression;
- [ ] bullish Complex Divergence regression;
- [ ] bearish mirrored Confirmation and Divergence regressions;
- [ ] missing-midpoint negative regression;
- [ ] complex-secondary negative regression;
- [ ] prefix/no-lookahead regression;
- [ ] 1.13 vs 1.618 ratio-selection regression;
- [ ] final confirmation fail-closed regression while projection coordinates remain unresolved;
- [ ] existing lifecycle Wilder RSI evidence remains explicitly non-BAMM.

## Next Phase after Phase 1 green

1. reconcile X-A price-projection coordinates from Volume Two figures/text and Volume Three examples;
2. freeze target-price formula and pattern-completion exception semantics;
3. add exact Confirmation Point tests and harmonic-confluence adapter;
4. only then expose BAMM to source-aligned lifecycle/workbench as a distinct evidence channel;
5. optional Acceleration Trigger remains a separate enhancement, not a shortcut around the core sequence.
