# CR-0070 — M6.5 Source Coverage Freeze

status: planned
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.5

## Objective

Freeze the three-book Source capability surface into a machine-validated ledger before the
TradingView-class M6.6 chart foundation begins.

## Scope

- upgrade SOURCE_COVERAGE to schema 2;
- normalize capability classification;
- bind Source/spec/code/tests/Decisions;
- freeze critical quarantine/unsupported states;
- add a CI verifier;
- harden CI supersession with workflow-level concurrency cancellation;
- preserve all existing M2/M3/M4 Source and evidence semantics.

## Acceptance

See `specs/m6-phase-5-source-coverage-freeze.md`.

## Non-goals

No pattern promotion, no Source Raw PRZ change, no new ratio, no empirical tuning, no M4 rewrite,
no BSE enablement and no trading execution.
