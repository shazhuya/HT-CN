# CR-0072 — M7.1 Prospective Evidence Accumulation Control Plane

status: implementing
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

## Second hosted validation

Repair workflow `35510111482` / #2408 on
`245ef70641c0308a9d33701509249a78db1cba06` passed Project OS, Source Coverage and Ruff 0/0.
Python then reported 892 passed / 9 failed, all in the legacy M4 wrapper-contract test file.

The evidence showed two operational-test issues: the legacy tests still required the retired
historical M4 branch/minimum-checkpoint contract, and the generated BAT text contained damaged
Windows backslashes because the GitHub write script had not used raw string material. The repair
rewrites the BAT byte-for-byte with preserved Windows paths and updates only the non-frozen wrapper
contract tests to the M7 canonical-main fail-closed rules.

## Activation validation

Hosted branch workflow `35510212083` / #2409 on
`f006ec0103a3a042ea5cb0ecf9e12268744bf3b7` passed Project OS, Source Coverage,
mutable Ruff 0/0, 900 Python tests / 0 warnings, continuation-bundle self-verification and Web
build. PR-only browser/Phase18/Phase21/M4 freeze gates remain pending.

This successful hosted Attempt is the activation anchor for M7.1.

