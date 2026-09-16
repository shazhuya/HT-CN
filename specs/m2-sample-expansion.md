# M2.14 — Prespecified 45-Symbol A-share Sample Expansion

## Goal

M2.12 found only 19 mature actionable completed reactions in the 13-symbol pilot, below the
60/30/10/10 research-governance floor. M2.14 expands the real-A-share research universe
without lowering that floor and without opening completed-reaction Holdout outcomes.

## Prespecified universe

The v2 universe contains 45 symbols across banking, brokerage, insurance, consumer, pharma,
auto, communications, semiconductors, electronic materials, new energy, resources, energy,
utilities, transport, construction and cyclical manufacturing.

The expansion list is selected from descriptive market/industry coverage before reading the
new Holdout outcomes. `name` and `bucket` are metadata only and are never model features.

## Snapshot policy

The pinned cutoff remains `2026-09-15`. M2.13 snapshot caching restores any already verified
same-cutoff symbol snapshots from the 13-symbol pilot and fetches only missing/incompatible
symbols. Every accepted symbol remains auditable by source and parquet SHA256.

## Split policy during expansion

No completed-reaction quality policy has yet been frozen. Therefore chronological
train/validation/holdout boundaries may be recomputed while expanding this prespecified
research universe. Once any completed-reaction quality policy is frozen, future boundary
changes require a new dataset version rather than silently moving the Holdout.

## Acceptance

The expansion is a sample-coverage exercise, not a success criterion for harmonic trading.
The run reports:

- provider/snapshot coverage;
- forming signal count;
- completed reaction count;
- mature actionable count;
- post-purge train/validation/holdout counts;
- Train/Validation descriptive T1/T2 rates only.

Holdout T1/T2 outcomes remain sealed regardless of whether the sample floor is reached.
Reaching the floor only permits the next research stage; it does not establish predictive
edge, profitability or a production trading rule.
