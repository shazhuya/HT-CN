# M2.22 — One-Time Type-I Holdout Evaluation

## Irreversible boundary

M2.21 committed the hypothesis, population, primary contrast, endpoint, sample floor and confidence-interval success criterion while the M2.17 Holdout was still sealed. M2.22 is a separate commit whose only new authority is to open that exact Holdout once.

The immutable pre-registration is `research/m2-type-i-holdout-prereg-v1.json`. The separate authorization file is `research/m2-type-i-holdout-open-v1.json` and must reference the M2.21 commit.

## Frozen primary question

Selected visible-data hypothesis: `full_prz_exit_by_t5`.

Population:

- source-aligned M2.17 Terminal Price Bar event;
- mature for the 20-bar reaction horizon;
- T2 still pending at T+5;
- belongs to the already-sealed M2.17 Holdout.

Exposure:

- full PRZ exit occurs at least once from T+1 through T+5.

Comparator:

- no full PRZ exit occurs from T+1 through T+5.

Endpoint:

- first T2 hit from T+6 through T+20.

## Confirmatory rule

Exactly one primary test is permitted.

- effect: exposure endpoint rate minus comparator endpoint rate;
- interval: 95% Newcombe score confidence interval for the difference of two independent proportions;
- minimum sample: 20 eligible Holdout cases in each group;
- `confirmed`: lower 95% interval bound is strictly greater than zero;
- `not_confirmed`: sample floor is met but the lower bound is not above zero;
- `inconclusive`: either group has fewer than 20 eligible cases.

No p-value fishing, alternate horizon, alternate exit deadline, alternate target or subgroup may replace the registered primary test.

## Secondary diagnostics

Direction, pattern family, source scale and instrument breakdowns are emitted only as descriptive diagnostics. They cannot rescue a failed primary test or create a new production rule.

## Reproducibility

The evaluator rebuilds the Terminal-Bar events from the byte-frozen 45-stock QFQ snapshot cache using the same manifest, cutoff and scales. Dataset/cutoff mismatch is a hard failure.

The exact M2.22 result must be committed to repository history in the following stage and the one-time authorization must then be closed. Repeated Holdout inspection is not part of iterative model development.

## Interpretation

Even a `confirmed` result is historical confirmatory evidence for one narrowly pre-registered path property. It is not a guarantee, return forecast, position-sizing instruction or trading recommendation, and it does not alter Carney geometry.
