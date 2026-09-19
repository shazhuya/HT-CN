# CR-0069 — M6.4 Repository Governance

status: planned
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.4

## Objective

Close the repository-governance phase without changing harmonic Source truth, M4 methodology,
Outcome Engine, market-data semantics, product trading semantics, or empirical claims.

## Current facts

1. historical stacked M5 pull requests are already closed/superseded under CR-0065;
2. pytest warning budget is already zero and CI fails on warning growth;
3. canonical main currently reports repository-wide Ruff debt below the frozen budget, but the debt
   remains non-zero and ISSUE-0068 still blocks quality closeout;
4. GitHub branch metadata reports `main protected=false`;
5. repository rulesets currently return an empty set;
6. the connected GitHub App receives HTTP 403 for the branch-protection endpoint and exposes no
   administration write action, so server-side protection cannot be enabled from this execution path.

## Must solve

1. reduce repository-wide Ruff debt in bounded, test-backed mechanical batches and lower the frozen
   budget after each verified reduction;
2. make the final Ruff baseline explicit and non-growing;
3. preserve warning budget zero;
4. record the exact server-side protection/ruleset evidence and permission boundary without
   pretending protection is enabled;
5. ensure Project OS, formal release, post-merge main validation and continuation artifacts agree;
6. leave M6.5 as the next task only after M6.4 internal governance gates are complete.

## Acceptance

See `specs/m6-phase-4-repository-governance.md`.

## Non-goals

No harmonic detector/PRZ/lifecycle changes, no M4 capture/outcome changes, no universe expansion,
no BSE enablement, no market-data repair, no trade execution and no profitability/statistical claims.
