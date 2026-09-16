# M2.15 — Completed-Reaction Quality Evidence

## Purpose

M2.11 corrected the completed-pattern reaction clock so reaction evidence begins only after the terminal Pivot is confirmed. M2.12 added a purged chronological Train / Validation / sealed Holdout calibration. M2.15 studies whether signal-time properties of an already completed source-valid harmonic structure are associated with stronger post-confirmation Type-I reactions.

This is a research layer only. It cannot create, delete, relabel or rescore a Carney pattern identity.

## Hard anti-leakage boundary

M2.15 consumes `m2-confirmed-completed-reactions.json`, the artifact emitted by M2.12 after Holdout outcomes have already been redacted. The quality module therefore never receives raw Holdout T1/T2 labels.

Train and Validation rows are reconstructed from the frozen M2.12 chronological boundaries and the exact forward observation-end date. Rows whose forward labels crossed a boundary were already purged and remain excluded.

## Fixed exploratory gate library

Numeric thresholds are learned from Train only and then reused unchanged on Validation.

Structural / geometry-quality gates:

- `geometry_top_half`
- `geometry_top_quartile`
- `narrow_prz_q1`
- `narrow_prz_q2`

Operational observability gates:

- `fast_confirmation_q1`
- `fast_confirmation_q2`

Source-conformity and scale context:

- `no_source_tolerance_required`
- `scale_5_plus`
- `scale_8_plus`

The layer label is part of the output so a low confirmation lag or larger Pivot scale is not mislabeled as superior harmonic geometry.

## Outcomes

The research target is post-confirmation reaction only:

- T1 = first Type-I reaction target for that schema;
- T2 = second Type-I reaction target for that schema.

Forming-PRZ touch, later reversal, profitability and trade execution are separate questions and are not substituted for these labels.

## Candidate semantics

A gate may be marked `consistent_t1_evidence` only when it has the configured minimum Train and Validation sample and raises T1 rate versus each split's own baseline in both splits. `t2_corroborates` additionally requires non-negative T2 lift in both splits.

Even then:

- `eligible_for_policy_freeze` remains `false`;
- the result is exploratory evidence, not a trading rule;
- Holdout remains sealed;
- family/symbol concentration must be checked before any future policy freeze.

## Sample governance

If M2.12 has not reached the prespecified completed-reaction 60/30/10/10 research floor, M2.15 returns `completed_reaction_quality_sample_insufficient_holdout_sealed` and does not search gates.

No sample floor may be reduced merely to obtain a positive result.
