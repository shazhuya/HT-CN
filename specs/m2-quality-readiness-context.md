# M2.10 Quality / Readiness / Context Separation

## Purpose

M2.8 and M2.9 deliberately began with a compact signal-time gate library so HT-CN could test whether any simple evidence survived purged Train/Validation and broad robustness checks. That stage produced several robust candidates, but it also exposed a semantic problem: not every useful signal-time feature means the same thing.

M2.10 therefore separates three concepts before any production quality policy can be frozen.

- **Quality**: structural evidence about the harmonic setup itself.
- **Readiness**: how close or timely the setup is relative to its projected PRZ.
- **Context**: measurement scale or market framing that changes how evidence should be interpreted.

This stage does not modify Carney identity, does not search arbitrary new cutoffs and does not open Holdout outcomes.

## Semantic layers

### Structural quality

The current structural-quality feature set is:

- `source_tolerance_used`
- `scale_support_count`
- `prz_width_ratio`

These describe geometry provenance, multi-scale support and PRZ convergence. They may be researched as quality evidence because they do not mechanically move the signal closer to the future event being measured.

### Readiness

The readiness feature set is:

- `distance_to_prz_ratio`
- `confirmation_lag_bars`

`distance_to_prz_ratio` is explicitly **not** allowed to masquerade as geometry quality. If the signal is already close to the PRZ, a later PRZ touch is mechanically easier. That can be useful for timing and monitoring, but it is not evidence that the harmonic geometry itself predicts better.

`confirmation_lag_bars` describes signal latency/timeliness and therefore belongs in the same operational layer.

### Context

The current context feature set is:

- `source_scale`

A pivot scale changes what swing structure is being measured. A preference for scale 3, 8 or 13 is therefore context evidence, not a universal quality score.

### Mixed gates

Any gate combining clauses from different semantic layers is labelled `mixed`. Mixed gates remain research diagnostics only. They cannot become a universal quality policy without a separately predeclared interaction study.

Examples:

- `scale8_narrow_q2`: context + quality
- `canonical_near_q2`: quality + readiness

## Pattern-family separation

A universal structural-quality gate must not be driven by one pattern identity.

HT-CN now groups identities into four research families:

- `ABCD`
- `XABCD`: Gartley, Bat, Alternate Bat, Butterfly, Crab, Deep Crab
- `SHARK`
- `FIVE_ZERO`

This grouping is only for calibration diagnostics. It does not merge or rewrite Carney identities.

For every strong structural-quality gate, M2.10 reports:

- per-pattern diagnostics;
- per-family diagnostics;
- per-scale diagnostics;
- gated-sample concentration;
- Train and Validation directional consistency.

A finding dominated by AB=CD can therefore be retained as an **ABCD-specific hypothesis** without being mislabelled as a universal harmonic-quality rule.

## Universal quality guard

A gate can become a `universal_quality_candidate` only when all of the following are true:

1. it already passed M2.9 robustness;
2. it belongs purely to the `quality` semantic layer;
3. pattern generalization passes;
4. family generalization passes;
5. scale generalization passes.

The generalization thresholds are research safeguards, not Carney rules.

### Pattern generalization

- at least 3 eligible identities in Train and Validation;
- favorable touch-up / retirement-down direction in at least two thirds of eligible identities;
- no single identity contributes more than 60% of gated observations.

### Family generalization

- at least 2 eligible families in Train and Validation;
- favorable direction in at least 75% of eligible families;
- no single family contributes more than 70% of gated observations.

### Scale generalization

- at least 3 eligible pivot scales in Train and Validation;
- favorable direction in at least two thirds of eligible scales;
- no single scale contributes more than 70% of gated observations.

These guards are intentionally conservative. A gate that fails universal generalization may still be documented as a family-specific or pattern-specific research hypothesis.

## Anti-leakage

M2.10 reuses the same purged chronological Train / Validation / sealed Holdout design.

- numeric cutoffs are still learned from Train only;
- Validation does not redefine numeric cutoffs;
- M2.10 does not create arbitrary new gate formulas;
- Holdout outcomes are not read;
- `policy_frozen` remains false.

A future policy-freeze stage must select and hash exact clauses **before** Holdout is opened once.

## Interpretation

The key distinction is:

> better readiness is not automatically better harmonic geometry.

A signal that is already near its PRZ can be operationally more actionable to monitor while carrying no extra evidence that its underlying Carney structure is superior.

Likewise, a result concentrated in AB=CD or scale 3 is not allowed to become a universal rule merely because aggregate Train and Validation statistics look favorable.
