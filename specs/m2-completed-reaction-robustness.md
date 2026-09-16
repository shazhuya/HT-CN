# M2.16 — Completed-Reaction Robustness

## Purpose

M2.15 can identify Train/Validation conditions associated with better post-confirmation T1/T2
reaction rates. M2.16 asks a harder question: does that evidence survive basic dependence and
generalization checks, or is it an artifact of a few symbols, a pattern family, one time slice,
or a proxy for the Pivot scale itself?

This stage **does not search for new gates**. It only stress-tests names already present in
`consistent_t1_candidates` from M2.15. Completed-reaction Holdout outcomes remain unavailable.

## Stress tests

For each M2.15 candidate M2.16 reports:

1. **Symbol concentration** — no single symbol may contribute more than 25% of gated Train or
   Validation observations.
2. **Leave-one-symbol-out** — aggregate T1 lift must remain positive after removing every
   individual symbol from each visible split.
3. **Pattern-family generalization** — a general candidate needs at least two jointly eligible
   families and positive within-family T1 lift in both Train and Validation.
4. **Chronological stability** — Train is divided into thirds and Validation into halves. At
   least two-thirds of eligible Train segments must retain positive T1 lift; both Validation
   halves must be eligible and positive.
5. **Scale diversity** — non-context evidence needs at least two source scales in Train and
   Validation and no single scale above 80% of gated observations.
6. **Semantic alias audit** — under the current fixed-scale confirmed-Pivot engine,
   `confirmation_lag_bars` may be exactly equal to `source_scale`. If a latency gate is therefore
   identical to a simple scale rule, it is reclassified as `context_scale_alias` and cannot be
   treated as independent quality evidence.

These thresholds are HT-CN research-governance choices, not Scott M. Carney rules.

## Policy boundary

`robust_research_candidate` is still not a trading rule. M2.16 always emits:

- `eligible_for_policy_freeze = false` for every gate;
- `policy_frozen = false` globally;
- `holdout_opened = false` globally.

Carney identity, Pivot selection, PRZ construction and Type-I reaction targets are immutable
with respect to these outcome statistics.

## Current expected interpretation

The 45-symbol M2.14 sample is large enough to open completed-reaction calibration, but the
visible Validation set is still modest. M2.16 is deliberately conservative: weakly supported
or semantically redundant evidence should be rejected rather than promoted to a production
filter. A result of **zero robust candidates** is valid evidence and must not trigger relaxed
criteria or an early Holdout opening.
