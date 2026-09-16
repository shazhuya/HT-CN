# M2 Autonomous Research CI

## Goal

HT-CN development must not rely on the user's Windows workstation for routine QA. M2 autonomous research therefore separates three environments:

1. Deterministic CI for code/math/UI regressions.
2. CI-accessible real A-share research snapshots for walk-forward and quality evidence.
3. The user's full local market database only for final production integration or issues that cannot be reproduced elsewhere.

## Research universe

`research/a-share-research-universe-v1.json` pins a small representative A-share universe and a fixed historical cutoff. Industry/style labels are descriptive metadata only and are never quality-model features.

The first universe intentionally spans consumer, AI chips, optical communication, electronics materials, precious metals, industrial power equipment, banking, insurance, medicine, cyclical resources, autos and new energy.

## Data policy

The autonomous research job fetches provider-adjusted QFQ history directly into CI artifacts. This is a research snapshot only. It does not replace the production raw+factor architecture and it must never be written back as the user's durable market database.

Each successful snapshot records SHA256 so provider restatements are detectable across runs.

External provider availability is evidence, not a truth override. A network/provider failure is reported explicitly and must never be converted into a positive or negative harmonic conclusion.

## Calibration policy

The CI job runs the same no-lookahead forming replay used by local calibration:

- confirmed Pivot events only;
- XABCD / AB=CD / Shark / 5-0 forming projections;
- late-signal detection;
- frontier retirement;
- exact completion-prefix matching;
- 60-bar outcome horizon.

After replay, the autonomous layer performs the same purged chronological Train / Validation / Holdout split. Numeric thresholds are learned from Train only. Validation confirms direction only. Holdout outcomes remain sealed.

Carney identity and PRZ construction are frozen and are never fitted to outcome statistics.

## CI behavior

The deterministic test job remains the blocking quality gate.

The real-market research job runs after deterministic tests on M2 branch pushes. It produces:

- normalized QFQ parquet snapshots;
- per-symbol source and SHA256 metadata;
- walk-forward counts;
- purged split metadata;
- Train/Validation quality-gate evidence;
- explicit provider failures;
- sealed Holdout metadata.

Its report is uploaded as a GitHub Actions artifact. Routine development should use these artifacts instead of asking the user to run `.bat` files or send screenshots.

## When the user's computer is allowed

Local execution is reserved for:

- full-market production database integrity/coverage;
- Windows-only path, permissions, process or environment issues;
- final release-level local integration;
- defects tied to private local files that are unavailable to CI.

Routine algorithm, UI, API, walk-forward, quality-gate and regression testing must stay autonomous.
