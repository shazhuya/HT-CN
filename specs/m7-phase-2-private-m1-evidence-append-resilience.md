# M7.2 — Private-M1 Evidence Append Resilience Repair

status: planned

## 1. Observed failure

The first M7 private run on `eca753f148871495482d86a69ca44f30c8730bb6` passed both immutable guards and M1, then QFQ stopped at 54/55. `SZSE.000001` failed because AkShare disconnected and BaoStock omitted 1991-04-13, 1991-04-20, 1991-05-04, 1991-07-20 and 1991-11-23. No authoritative capture was committed. The failure bundle also contained stale disposable reports from an older run.

## 2. Legacy-calendar bridge

A missing factor session may be bridged only when it is an internal Saturday session from 1992 or earlier, bracketed by real factors, and the entire gap is strictly before the frozen 420-bar formal prospective-capture window. The synthetic factor is deterministic linear interpolation between the two real brackets and is audited as `legacy_saturday_outside_formal_capture_window`.

The bridge is forbidden inside the formal capture window. Raw OHLCV remains durable truth.

## 3. Local-first repair

If a current formal view is raw, readiness checks the existing local factor parquet before network fetch. A valid bounded repair is written atomically and must re-prove a formal QFQ view.

## 4. Failure-bundle freshness

Before M1, the wrapper removes disposable M1/QFQ, snapshot, health, transition, observation, outcome, M7-status and transport-ZIP outputs. Immutable capture transactions and committed outcome snapshots are never deleted.

## 5. Deterministic step status

Every step exit variable starts at failure `1` and is overwritten only when that step actually runs.

## 6. Frozen boundaries and acceptance

No frozen methodology or Outcome Engine path may change. Before merge: targeted tests, full Python/zero-warning/Ruff, Web/browser/Phase18/Phase21, Project OS, Source Coverage, methodology 37/37 and Outcome 4/4 must all pass. After canonical-main validation, rerun exactly `运行M7前瞻证据积累.bat`; ISSUE-0069 closes only after the real rerun and evidence acceptance.
