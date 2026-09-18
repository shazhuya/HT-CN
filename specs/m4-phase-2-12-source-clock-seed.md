# M4 Phase 2.12 — Frozen Source-Clock Seed and Methodology v4

## Purpose

An outcome-enrolled harmonic candidate may later disappear from the scanner before a Source
Terminal Price Bar has been observed.

D-032 already preserves the underlying security's future market path through scanner-absent
follow-up rows. That is necessary but not sufficient to reconstruct the existing Source execution
clock.

The Source execution observer also requires the original observable forming-signal time and the
reaction anchor price. Phase 2.12 freezes those facts at enrollment so future source-event
research does not depend on continued scanner visibility.

## Existing source-clock inputs

The current Source execution observer uses:

- signal bar;
- harmonic direction;
- frozen Source Raw PRZ;
- reaction anchor price;
- future high/low market observations.

The forming payload already exposes:

- `execution_clock.signal_bar`;
- `execution_clock.signal_clock_basis`;
- `execution_clock.reaction_anchor_label`;
- `execution_clock.reaction_anchor_price`.

No new harmonic geometry rule is introduced here.

## Frozen journal seed

Formal journal rows may carry:

- `source_signal_trade_date`;
- `source_signal_clock_basis`;
- `source_reaction_anchor_label`;
- `source_reaction_anchor_price`.

The signal bar is converted to its trade date while the forming signal is still observable.

Current signal-clock basis:

`last_frontier_pivot_confirmed_at=index+scale`

Current reaction-anchor mapping follows the existing execution-clock implementation:

- Shark / 0XABC -> B;
- XABCD / standalone AB=CD -> A.

## Outcome enrollment

A prospective-new candidate may not enter the strict outcome cohort without a complete
Source-clock seed.

Missing seed:

`source_clock_seed_unresolved`

A signal date after the observation date:

`source_clock_seed_after_observation`

This gate is in addition to the existing requirements for:

- formal QFQ price basis;
- traded first observation;
- forming/pre-terminal state;
- resolved Source Raw PRZ;
- source-fidelity-allowed pattern.

## Committed capture schema v5

Schema v5 adds source-clock seed integrity.

For a journal row the four seed fields must be either:

- all absent; or
- all present and internally coherent.

Partial seed is a hard blocker.

Seedless rows may still be stored as evidence, but they cannot enter the future outcome cohort.

Follow-up rows do not duplicate the seed. The authoritative enrollment row remains the frozen
seed source.

Schemas v1-v4 remain readable for historical/migration audit, but an active older-schema chain
cannot silently append v5.

## Prospective observation schema v4

For every outcome-enrolled candidate, the candidate summary freezes:

`enrollment_source_clock_seed`

with:

- pattern ID;
- schema;
- direction;
- scale;
- enrollment lifecycle state;
- frozen Source Raw PRZ low/high;
- source signal trade date;
- source signal clock basis;
- reaction anchor label;
- reaction anchor price.

The seed is immutable enrollment provenance. Later completed/scanner-absent payloads are not
required to recreate the forming execution_clock.

## Scanner disappearance

Scanner disappearance still means only:

`scanner_presence = absent`

It does not mean:

- invalidated;
- completed;
- lifecycle continuation;
- reappearance.

The future source-event path can nevertheless be reconstructed from:

1. frozen enrollment source-clock seed;
2. frozen Source Raw PRZ/direction;
3. authoritative scanner-present market observations;
4. scanner-absent cohort follow-up market observations.

This removes scanner-survivorship censoring from future Source Terminal / Type-I / Type-II
research.

## Price-basis boundary

D-034 remains active.

If the price basis changes after enrollment, Phase 2 records the drift but does not automatically
rebase the frozen Source PRZ or reaction anchor.

Cross-basis source-event or performance calculations remain unresolved until a separately
preregistered rebasing protocol exists.

## Methodology v4

Because strict outcome enrollment and future source-event reconstructability changed, the
methodology contract advances from v3 to v4.

The conservative component path set remains 37 files.

Exact methodology-v4 freeze commit:

`c774c54928c33361952bf1a612a8555633449625`

No post-T0 future committed capture existed before this freeze. No future evidence is migrated,
rewritten or mixed across methodologies.

## Source boundary

This source-clock seed is HT-CN prospective-evidence engineering.

It does not claim Carney specifies:

- this database schema;
- this seed serialization;
- A-share QFQ mechanics.

Carney's Source/Terminal/Type-I/Type-II concepts remain the methodology reference; HT-CN is
preserving the already-observable inputs needed to evaluate those concepts prospectively.

## Outcome boundary

Phase 2.12 still does not compute:

- return;
- MFE / MAE;
- win rate;
- alpha;
- expected return;
- buy/sell ranking.
