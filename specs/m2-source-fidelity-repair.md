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

Until runtime consumes the M2.17 no-lookahead Terminal-Bar pipeline, D-based T1/T2 values must be
shown as **retrospective** evidence only.

## Invariant B — PRZ data requires explicit semantics

A single pair named `price_low/price_high` is no longer sufficient as a conceptual model.

HT-CN distinguishes:

- **component envelope** — outer envelope of every stored measurement/variant; audit data only;
- **ideal convergence core** — current HT-CN narrow convergence selection used by display and
  geometry quality;
- **source Raw PRZ** — to be frozen per pattern from textbook/figure-level evidence; it must not
  be guessed from either of the two objects above;
- **Terminal extreme** — real price extreme of the source-aligned T-Bar;
- **PEZ** — source PRZ plus the T-Bar extreme, following Volume Three execution semantics.

Legacy `price_low/price_high` currently remain aliases for the ideal convergence core only for
compatibility. UI and docs must not call that pair the entire source PRZ.

## Invariant C — Type-II requires full retest before confirmation

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

Only states after the full retest may be called Type-II candidates/confirmations.

## Invariant D — Wilder RSI evidence is not RSI BAMM

The current lifecycle module records a simple Wilder RSI extreme-zone reversal. It is an
auxiliary indicator evidence layer only.

It must never be named or implied to be RSI BAMM.

A future RSI BAMM implementation must independently model the Volume Two multi-step process,
including the complex RSI structure, trigger bar, reaction, divergence, 1.13/1.618 confirmation
and coordinated harmonic pattern completion.

## Invariant E — 5-0 is quarantined from default production output

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

## Invariant F — Geometry score cannot rescue identity

Existing behavior remains frozen:

- source-backed hard identity constraints decide completed/rejected;
- geometry score ranks/characterizes only candidates that already passed identity;
- statistics, A-share context, indicator evidence and UI preference cannot revive a rejected
  Carney identity.

## Book Golden Set requirement

Synthetic fixtures are necessary but insufficient.

Before source-fidelity repair closes, the repository must contain a textbook regression ledger
covering, where supported by the books:

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

Each case must record source volume/page or figure, source measurements, expected identity,
expected PRZ measurements, completion semantics and any deliberate HT-CN approximation.

## Acceptance order

M3 normal feature work remains paused until these gates are satisfied in order:

1. Type-II full-retest semantics and non-BAMM indicator labels — implemented in M2.26.
2. PRZ component-envelope vs ideal-core semantics — implemented in M2.26; source Raw PRZ still
   requires Book Golden Set resolution.
3. 5-0 default-production quarantine — implemented in M2.26.
4. Runtime data contract exposes a source-aligned Terminal-Bar/PEZ event independently from the
   retrospective D audit.
5. Book Golden Set freezes Raw PRZ component selection and reconciles 5-0 Volume Two/Three.
6. M3 T1/T2 overlays switch from retrospective D targets to source-aligned Terminal-Bar targets.
7. Only then resume normal Type-II/product expansion.

## Research preservation

Existing frozen Holdout/external-replication artifacts are historical research records and must
not be silently rewritten. If a repaired runtime definition changes eligibility, create a new
versioned prospective protocol rather than retroactively editing consumed results.
