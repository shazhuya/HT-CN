# CR-0073 — M7.2 Private-M1 Evidence Append Resilience Repair

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: eca753f148871495482d86a69ca44f30c8730bb6
target: main
milestone: M7.2

## Trigger

The first real M7 canonical-main private run failed closed on 2026-09-20. Both immutable guards and M1 passed, but strict QFQ readiness stopped at 54/55. `SZSE.000001` could not become formal-QFQ: AkShare disconnected and BaoStock omitted five raw-history Saturday sessions from 1991.

The run correctly committed no authoritative capture. The uploaded transport bundle SHA-256 `a8d9ce7a8b5aabbc9bea56be4913972f8298fc6462f2b1c4b9d42c8157cd2c15` also revealed that disposable reports from an older failed run could remain on disk and be included in a later failure bundle.

## Objective

Repair the mutable M7 preparation/control layer without changing harmonic methodology, Source semantics, lifecycle, Outcome Engine semantics, or the full-universe fail-closed requirement.

## Scope

- repair already-local factor histories before network requests;
- allow a deterministic audited bridge only for early A-share Saturday raw sessions when the entire gap lies strictly before the frozen 420-bar formal capture window;
- keep all strict rules inside the formal analysis window;
- clear disposable run reports before each run so failure bundles cannot silently carry stale reports;
- initialize every wrapper step exit code;
- add regression tests and governance evidence;
- keep Project OS Resume Pack bounded by indexing active decisions and non-closed issues instead of duplicating closed governance history.

## Non-goals

No change to any 37 frozen M4 methodology components, any 4 frozen Outcome Engine components, historical committed evidence, partial-universe capture, statistical inference, or trading execution.

## Acceptance

See `specs/m7-phase-2-private-m1-evidence-append-resilience.md`.
