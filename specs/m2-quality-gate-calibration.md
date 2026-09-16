# M2.8 Quality Gate Calibration

## Purpose

HT-CN must not change Carney identity rules to improve historical outcomes. M2.8 studies only whether already-valid forming signals contain stable, signal-time quality evidence that can reduce frontier noise.

## Why sample expansion comes first

The first no-lookahead replay used only three QFQ instruments. That is enough to validate the replay engine, but not enough to freeze a market-wide quality policy. The current initialized raw SSE/SZSE universe must therefore be expanded into resumable QFQ factor coverage before any gate is promoted.

`运行M2扩大样本并质量校准.bat` performs four steps in one run:

1. Build/refresh QFQ factors for every initialized SSE/SZSE raw dataset. Existing current factors are skipped.
2. Re-run no-lookahead forming walk-forward on the enlarged QFQ universe.
3. Rebuild the purged chronological Train / Validation / Holdout split.
4. Evaluate a small, predeclared quality-gate library on Train and Validation only.

## Holdout discipline

Holdout outcome statistics remain sealed. The quality-gate script refuses to run if the time-split artifact reports an opened holdout.

No gate may use:

- future PRZ touch,
- later completion,
- later return,
- later retirement,
- any other post-signal outcome

as an input feature.

## Allowed signal-time evidence

The initial gate library is intentionally small:

- canonical geometry vs source tolerance,
- number of supporting pivot scales,
- source pivot scale,
- PRZ width relative to the reference swing,
- current distance from close to PRZ,
- pivot confirmation lag.

Numeric cutoffs use Train Q1/median values learned by M2.7. Validation reuses those values unchanged.

## Candidate promotion

A gate is only a **strong research candidate**, not a production rule, when:

- Train sample >= 25 and Validation sample >= 10,
- touch direction improves in both Train and Validation,
- retirement direction improves in both Train and Validation,
- and Train shows at least +3 percentage points touch improvement or -5 percentage points retirement reduction.

Completion is reported but is not optimized at this stage because completed events are too sparse.

The gate ranking score is Train-only. Validation can confirm direction but cannot redefine a gate or its thresholds.

## Freeze policy

M2.8 never freezes a production quality policy automatically. A policy may only be frozen after:

1. materially broader QFQ symbol coverage,
2. stable Train/Validation direction,
3. review of per-pattern and per-scale concentration,
4. an explicit decision to seal the chosen policy before opening Holdout once.
