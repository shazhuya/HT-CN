# CR-0068 — M6.3 Universe Coverage Contract

status: planned
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.3

## Objective

Resolve ISSUE-0062 by freezing and implementing distinct listed, initialized,
formal-QFQ-ready, scanner, research-scanner, operator and candidate-set semantics.

## Triggering evidence

The accepted M6.2 real Private-M1 closeout proved an operationally ready default
product lane with 55 initialized SSE/SZSE instruments while the listed SSE/SZSE
security-master scope contained 5218 instruments. That warning is valid evidence of a
coverage gap and must not be hidden or reworded as full-market coverage.

## Must solve

1. machine-readable universe layers with deterministic hashes;
2. catalog-backed initialized scope, not raw directory-glob scope;
3. BSE kept deferred from default product scope;
4. formal-QFQ-ready separated from raw-fallback product readiness;
5. product scanner and operator universe equality;
6. candidate set explicitly downstream and never a coverage denominator;
7. coverage claims prohibited from calling initialized coverage full A-share coverage;
8. regression tests and Project OS/CI continuity.

## Acceptance

See `specs/m6-phase-3-universe-coverage-contract.md`.

## Non-goals

No bulk data initialization, no QFQ repair/download, no BSE default enablement, no
harmonic Source/PRZ/lifecycle changes, no M4 methodology/Outcome Engine changes, no
trade execution, and no profitability/statistical claims.
