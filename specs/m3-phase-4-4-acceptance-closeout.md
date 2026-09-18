# M3 Phase 4.4 — Acceptance Evidence / Real-M1 Closeout

## Goal

Make PR readiness an auditable machine-readable decision instead of a manual interpretation of scattered logs.

Phase 4.4 does not change harmonic identity, lifecycle semantics or trading logic.

## Evidence files

Formal closeout uses four reports produced from the same Git commit:

- `artifacts/reports/m3-workbench-acceptance.json`
- `artifacts/reports/m3-metadata-tradability-smoke.json`
- `artifacts/reports/m3-product-contract-smoke.json`
- `artifacts/reports/m3-context-sync-summary.json`

Every report carries `code_head`. Evidence from any other commit is stale and is a hard blocker.

## Formal deterministic acceptance

`运行M3工作台验收.bat` / `scripts/qa_local.py` records six gates:

1. complete Python regression;
2. TypeScript/Web build;
3. strict real-M1 metadata/tradability smoke;
4. real-M1 product payload contract smoke;
5. local API + Workbench startup;
6. full Playwright acceptance.

Formal metadata acceptance requires readable representative MAIN / STAR / CHINEXT parquet histories.

## Context synchronization

`运行M3上下文数据同步.bat` performs the network/data refresh separately from deterministic code acceptance.

Operational states:

- `all_steps_completed`
- `degraded`
- `partial_failure`

`partial_failure` is a hard blocker.

`degraded` may remain a warning when the system preserved a complete prior membership snapshot and local analysis still operates fail-safe. No degradation is silently converted to current evidence.

Positive-evidence-only suspension coverage is a known surfaced limitation, not complete proof of daily tradability.

## PR readiness

`scripts/m3_pr_readiness.py` produces:

- `m3-pr-readiness.json`
- `m3-pr-readiness.md`

Hard blockers include:

- stale/missing report for current HEAD;
- failed formal workbench acceptance;
- missing MAIN / STAR / CHINEXT real parquet coverage;
- real-M1 product-contract failure or issue count > 0;
- no successful real-M1 analysis;
- context structural failure.

Warnings include:

- positive-evidence-only daily event coverage;
- degraded but fail-safe context refresh;
- no harmonic candidate appearing in the small real-M1 smoke sample.

Warnings remain visible and do not become hidden scores.

## One-click closeout

`运行M3最终收口.bat` executes:

1. deterministic workbench acceptance;
2. real four-layer context synchronization;
3. PR-readiness evaluation.

The batch continues to the readiness evaluator even when an earlier stage fails so the user receives one complete blocker report.

## Frozen boundaries

A READY result does not remove any existing source-fidelity boundary:

- 5-0 remains production-quarantined;
- Alternate Bat remains fail-closed;
- BSE remains deferred;
- incomplete daily-event coverage remains explicitly unresolved where applicable.

READY is a code/evidence merge-readiness state, not an investment score, alpha claim or trade permission.
