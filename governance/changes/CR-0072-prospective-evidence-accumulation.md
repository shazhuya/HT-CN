# CR-0072 — M7.1 Prospective Evidence Accumulation Control Plane

status: planned
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M7.1

## Objective

Start M7 from canonical main without changing frozen harmonic Source semantics, the M4 capture
methodology, or the frozen Outcome Engine.

The first delivery makes prospective evidence accumulation an explicit canonical-main operating
workflow and adds an evidence-only accumulation status report.

## Scope

- replace the historical M4 work-branch preflight in the one-click capture wrapper with a strict
  clean-`main` + freshly fetched `origin/main` identity preflight;
- preserve the frozen M4 capture and Outcome Engine guards before any private-M1 update or
  authoritative capture;
- add `运行M7前瞻证据积累.bat` as the M7 operator entry point;
- add a read-only M7 accumulation status report over the existing authoritative committed capture
  chain, prospective observation panel, and committed outcome snapshots;
- keep ISSUE-0066 explicit: the status report never converts sample accumulation into win-rate,
  alpha, profitability, significance, or buy/sell claims;
- add tests for the control-layer status semantics.

## Acceptance

See `specs/m7-phase-1-prospective-evidence-accumulation.md`.

## Non-goals

No Carney ratio or pattern-identity change, no Source Raw PRZ/Source Clock/lifecycle change, no
M4 methodology component change, no Outcome Engine component change, no 5-0 promotion, no
Alternate Bat promotion, no BSE enablement, no empirical threshold tuning, and no trading
execution.

## Activation rule

This Change remains `planned` until a hosted branch workflow proves the candidate green. Only
then may Project OS atomically activate M7.1 and bind the successful hosted Attempt.

## First hosted validation

Branch workflow `35510029970` / #2407 on candidate
`6f2c673d93fb3b6d20c5955a49d0ec0b6577d93e` passed Project OS and Source Coverage,
then failed the zero-debt Ruff gate with exactly three new-code findings:
`I001=1`, `BLE001=1`, and `UP035=1`.

No Python tests, browser gates, or M4 freeze gates ran after the lint failure. The repair is limited
to import ordering, `collections.abc` typing imports, and narrowing the status-script exception
boundary. No Source, capture-methodology, Outcome Engine, or evidence semantics change.

