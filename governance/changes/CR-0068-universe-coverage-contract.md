# CR-0068 — M6.3 Universe Coverage Contract

status: implementing
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


## First hosted candidate

The initial implementation candidate on head `067ff916247d4ecd31ef170a679305057170bc6c`
passed PR workflow `35459245173` / run #2245:

- Project OS: success;
- Ruff budget: success;
- Python tests: success;
- Web build: success;
- existing browser acceptance: success;
- Phase18 browser/evidence: success;
- Phase21 dynamic browser/evidence: success;
- M4 methodology freeze: success;
- Outcome Engine freeze: success.

After that green candidate, review identified one additional fail-closed requirement: same-default-exchange
parentage errors must not be silently filtered. The branch now treats initialized-not-listed and
formal-QFQ-not-initialized SSE/SZSE members as explicit invariant failures. A fresh hosted validation
is required for the hardened tree before merge or closure.
