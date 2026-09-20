# CR-0070 — M6.5 Source Coverage Freeze

status: implementing
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


## Activation evidence

Hosted branch workflow `35485130202` / #2363 on head
`aaa47f49ca899cc8c004eb5cc7b16cb966ce143e` passed:

- Project OS v2 integrity;
- M6.5 Source Coverage verifier: valid, schema 2, 18 items, 0 Partial items, 0 errors;
- mutable Ruff: 0 / budget 0;
- Python: 896 passed;
- pytest warnings: 0;
- Web build: success.

Workflow-level supersession was also observed directly: superseded push run #2357 and PR run #2362
were automatically cancelled when newer commits arrived on the same ref.

This evidence activates M6.5. Full PR-only browser/Phase18/Phase21/M4 freeze gates remain required
before any ready-to-merge or closeout state.
