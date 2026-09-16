# M2.26 — Source Fidelity Repair

## Status

This stage interrupts normal M3 product expansion. It exists because a source review against
Scott M. Carney *Harmonic Trading* Volumes One, Two and Three found that several research
corrections had not yet become runtime/product invariants.

The repair is deliberately conservative: preserve validated geometry/data work, stop publishing
source-conflict semantics, and make uncertainty explicit rather than inventing a new rule.

## Authority and layer boundary

1. Carney Volume One / Two / Three define harmonic identity, source measurements and the
   reaction/reversal execution concepts.
2. HT-CN may add A-share context, ranking, statistics, risk controls and UI explanation only in
   separate layers.
3. An HT-CN enhancement must never silently rewrite a Carney identity or PRZ definition.
4. A research approximation must be labelled as such and must not be promoted to production
   merely because tests or historical statistics are green.

## Invariant A — Two clocks must never be collapsed

### Geometry / retrospective clock

A right-confirmed Pivot can establish a historical D point and validate completed geometry.
Post-D audits are useful for retrospective structural research.

This clock is **not** source-aligned execution observability.

### Execution / Terminal Price Bar clock

Volume Three execution semantics are driven by a no-lookahead forming projection and the first
still-valid price bar that tests the final/extreme measurement of the source PRZ.

The official sequence is:

`forming projection -> source PRZ entry -> Terminal Price Bar -> PEZ -> T-Bar+1 -> Type-I`

The workbench must not label a completed D Pivot as an observed Terminal Price Bar unless the
source-aligned execution-clock event exists independently.

For the current pivot detector, a frontier pivot is observable at
`confirmed_at = pivot.index + scale`. Runtime execution observation starts **after** that bar.
The API must expose this clock basis rather than silently starting from the historical pivot bar.

## Invariant B — Identity uses the harmonic ratio family, not arbitrary points inside a band

Carney's standard harmonic structures use specific harmonic measurements. A C point that merely
falls numerically somewhere between 0.382 and 0.886 is not automatically equivalent to a C point
aligned with one of the source harmonic ratios.

HT-CN therefore freezes the current standard C family as discrete measurements:

- 0.382
- 0.500
- 0.618
- 0.707
- 0.786
- 0.886

BC completion measurements are likewise represented as discrete harmonic projections rather than
one synthetic continuous projection band.

The current nearest-family 3% matching threshold is explicitly an **HT-CN operational tolerance**.
It is not claimed as a universal Carney source constant.

## Invariant C — PRZ data requires explicit semantics

A single pair named `price_low/price_high` is no longer sufficient as a conceptual model.

HT-CN distinguishes:

- **component envelope** — outer envelope of every stored measurement/variant; audit data only;
- **ideal convergence core** — current HT-CN narrow convergence selection used by display and
  geometry quality;
- **source Raw PRZ** — to be frozen per pattern from textbook/figure-level evidence; it must not
  be guessed from either of the two objects above;
- **Terminal extreme** — real price extreme of the source-aligned T-Bar;
- **PEZ** — source PRZ plus the T-Bar extreme, following Volume Three execution semantics.

Legacy `price_low/price_high` remain compatibility aliases for the ideal convergence core only.
UI and docs must not call that pair the entire source PRZ.

### API v2 price-zone contract

Every PRZ payload exposes:

```text
prz.ideal_core
prz.component_envelope
prz.source_prz
```

The top-level response publishes:

```text
price_zone_contract.version = 2
price_zone_contract.dynamic_layer = execution_clock.pez
price_zone_contract.fail_closed_without_source_prz = true
price_zone_contract.legacy_price_low_high_mean = ideal_core
```

PEZ is not a static PRZ property. It may appear only under `execution_clock.pez` after a source
PRZ is frozen and a Terminal Price Bar is actually observed.

## Invariant D — Type-II requires full retest before confirmation

A mere secondary overlap is not a confirmed Type-II event.

Retrospective state sequence:

1. initial reversal-direction exit;
2. secondary PRZ entry/overlap;
3. **full retest of the original PRZ terminal side**;
4. Type-II Terminal Price Bar;
5. post-retest price confirmation;
6. separate indicator confirmation.

HT-CN therefore uses these states:

- `not_candidate`
- `partial_retest_only`
- `full_retest_waiting_price`
- `price_confirmed_no_rsi`
- `price_and_rsi_confirmed`

Only states after the full retest may be called Type-II candidates/confirmations. If source PRZ
is unresolved, Type-II must fail closed with `source_prz_unresolved`.

## Invariant E — Wilder RSI evidence is not RSI BAMM

The current lifecycle module records a simple Wilder RSI extreme-zone reversal. It is an
auxiliary indicator evidence layer only.

It must never be named or implied to be RSI BAMM. The payload explicitly records
`indicator_evidence_is_rsi_bamm = false`.

A future RSI BAMM implementation must independently model the Volume Two multi-step process,
including the complex RSI structure, trigger bar, reaction, divergence, 1.13/1.618 confirmation
and coordinated harmonic pattern completion.

## Invariant F — 5-0 is quarantined from default production output

Volume Two defines the 5-0 structural PRZ around the 50% BC retracement and Reciprocal AB=CD.
Volume Three adds conditional execution refinement involving where Reciprocal AB=CD completes
relative to the 50% level and the 61.8% make-or-break/entry consideration.

The previous implementation compressed these concepts into a generic 50%-61.8% band and
required Reciprocal AB=CD to converge inside that band. That interpretation is not source-cleared.

Therefore:

- the dedicated 5-0 evaluator remains available for research and reconciliation;
- the default engine/Scanner/workbench does **not** emit 5-0;
- research must explicitly pass `include_source_conflict_patterns=True` to inspect it;
- production eligibility remains blocked until Volume Two / Volume Three figure-level Golden
  Cases reconcile the structural PRZ and execution refinement.

## Invariant G — Shark uses its own first-target contract

Shark is a reaction-oriented precursor to 5-0 and must not be forced through generic XABCD
T1/T2 semantics.

The engine retains three auditable post-C measurements:

- 50% BC retracement;
- 61.8% BC retracement;
- Reciprocal AB=CD, with prospective CD measured against the earlier AB counter-move.

Volume Three management is encoded as:

`initial_target = first encountered of (50% BC, Reciprocal AB=CD)`

"Lesser / comes first" is evaluated by reaction **distance from C**, not by numeric price value,
so bullish and bearish structures are symmetric. Ties remain explicit. The 61.8% measurement is
retained as a later 5-0/risk measurement and is not mechanically renamed Shark T1.

## Invariant H — Geometry score cannot rescue identity

Existing behavior remains frozen:

- source-backed hard identity constraints decide completed/rejected;
- geometry score ranks/characterizes only candidates that already passed identity;
- statistics, A-share context, indicator evidence and UI preference cannot revive a rejected
  Carney identity.

## Book Golden Set requirement

Synthetic fixtures are necessary but insufficient.

The repository must maintain a textbook regression ledger covering, where supported by the books:

- AB=CD
- Gartley
- Bat
- Alternate Bat
- Butterfly
- Crab
- Deep Crab
- Shark
- 5-0
- Terminal Price Bar / overspill / PEZ
- Type-I
- Type-II
- representative RSI BAMM sequencing (future module)

Each case records source volume/page or figure, source measurements, expected identity, expected
PRZ measurements, completion semantics and any deliberate HT-CN approximation.

## What M2.26 deliberately leaves unresolved

The repair must **not** invent answers for these items merely to produce live-looking states:

- per-pattern `source_prz_low/high` for Gartley / Bat / Alternate Bat / Butterfly / Crab / Deep Crab;
- which AB=CD variants belong to each executable source PRZ;
- how each source C ratio selects the executable BC measurement inside Raw PRZ;
- Shark source PRZ terminal-side freeze;
- 5-0 Volume Two / Volume Three figure-level reconciliation;
- full RSI BAMM state machine.

Until each item is resolved by the Book Golden Set, the corresponding execution state remains
`unresolved_fail_closed`.

## Acceptance order

M3 normal feature work remains paused until these gates are satisfied in order:

1. Type-II full-retest semantics and non-BAMM indicator labels — implemented.
2. Discrete harmonic-family identity checks — implemented.
3. PRZ component-envelope / ideal-core / source-PRZ separation — implemented.
4. 5-0 default-production quarantine — implemented.
5. Source-aligned Terminal-Bar/PEZ runtime contract — implemented for current forming XABCD/AB=CD;
   unresolved source PRZ correctly fails closed.
6. Shark first-of-50%-or-Reciprocal target semantics — implemented.
7. API v2 price-zone contract — implemented while preserving legacy aliases.
8. Deterministic Python + Web + Playwright CI must be green.
9. Merge M2.26, then continue source PRZ Golden Set on a separate branch before replacing M3
   retrospective overlays with live execution-clock targets.

## Research preservation

Existing frozen Holdout/external-replication artifacts are historical research records and must
not be silently rewritten. If a repaired runtime definition changes eligibility, create a new
versioned prospective protocol rather than retroactively editing consumed results.
