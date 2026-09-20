# CR-0071 — M6.6 Interactive Harmonic Chart Foundation

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.6

## Objective

Implement the TradingView-class interactive production chart required by D-069 without moving
harmonic Source truth into the chart library.

## First delivery

- Lightweight Charts candlestick foundation;
- shared canonical time/price coordinate adapter;
- observed harmonic nodes/legs and current PRZ/lifecycle overlays;
- crosshair identity readout;
- focus/reset interaction;
- browser verification that viewport changes do not rerun harmonic analysis.

## Acceptance

See `specs/m6-phase-6-interactive-harmonic-chart-foundation.md`.

## Non-goals

No harmonic formula change, Source promotion, M4 mutation, universe change, empirical tuning or
trade execution.


## Activation evidence

Hosted branch workflow `35486506393` / #2377 on head
`680d7a179d1179acb71659743d9423dc6bcb9393` passed:

- Project OS v2 integrity;
- M6.5 Source Coverage freeze gate;
- mutable Ruff: 0 / budget 0;
- Python: 896 passed;
- pytest warnings: 0;
- Web build: success.

The candidate already contains the first production interactive chart implementation. Full PR-only
browser, Phase18, Phase21 and immutable M4 freeze gates remain required before this delivery can be
accepted.


## First full-PR failure

PR #58 workflow `35486604600` / #2379 reached the real Chromium gate and failed 3 of 25
browser tests while 22 passed:

1. migrated Type-I target labels omitted the existing `已到达 / 待到达` visible state text;
2. migrated Source Raw PRZ / PEZ groups did not preserve the legacy
   `source-prz-zone / source-pez-zone` test identities;
3. wheel input did not reliably schedule HT-CN overlay reprojection from the inner chart-host
   event boundary.

These are renderer-contract defects, not Source-methodology failures. The repair preserves the
existing UI semantics and moves wheel/pointer reprojection capture to the outer chart stage. Tests
remain unchanged.

## Second full-PR failure

PR #58 workflow `35486769140` / #2381 on repair head
`5ba734ee9da3490e9fe8df78402d0e8154959a71` passed 24 of 25 browser tests. The lifecycle-label and
Source-zone compatibility repairs passed. The remaining M6.6 test observed no viewport-version
increment after the wheel event burst.

The event reached the interactive chart path, but the overlay scheduler cancelled and replaced its
pending animation frame on every high-frequency viewport event. The next repair coalesces repeated
events into the first pending frame so interaction cannot starve overlay reprojection. Tests and
Source semantics remain unchanged.

## Local repair validation

The repaired web production build succeeds. Project OS integrity also succeeds on the clean repair
commit. A full local Python run reported 895 passed and one failure in the pre-existing real-process
lock timing test. An isolated rerun confirmed that the lock serialized correctly but the spawned
waiter recorded only 0.04 seconds after process startup, below the test's 0.10-second timing floor.
This environment-sensitive failure is unrelated to the chart-only implementation; the unchanged
Python suite remains required to pass in Hosted CI.

## Third full-PR failure and input-boundary repair

PR #58 workflow `35499794939` / #2395 on head
`2dc9553ef73973434f9b2aa940aee653db49eb7c` again passed 24 of 25 browser tests. Its push workflow
passed Project OS, Source Coverage, Ruff, all 896 Python tests, zero warnings and the web build. The
remaining test showed that the third-party chart canvas boundary still did not deliver Playwright's
wheel input to the component-level chart-stage listener.

The repair captures wheel input at `window` capture scope and filters it to the current chart-stage
rectangle before incrementing the overlay projection version. This keeps unrelated page scrolling
out of the overlay path while removing dependence on the chart library's internal canvas event
propagation. The existing browser contract remains unchanged.

## Browser targeting diagnosis

PR #58 workflow `35501178834` / #2397 on head
`7b0897d2a4f29a781242ed642a0f3d2b55099680` proved that even `window` capture received no wheel
event. The chart is below the initial browser viewport; the test used its page bounding box without
first scrolling it into view, so the synthetic mouse coordinates never targeted the rendered page.

The next candidate restores component-scoped chart-stage capture and makes the browser test scroll
the stage into view before reading its box and sending mouse input. This is an interaction-fixture
repair, not a weakened assertion: the same viewport-version, no-recompute and canonical-identity
checks remain in place.

## Full PR validation

PR #58 workflow `35501377878` / #2399 on head
`9a6805abf597a0e7306db26db81c12aaf9630c97` passed:

- Project OS and M6.5 Source Coverage integrity;
- mutable Ruff 0 / budget 0;
- 896 Python tests with zero warnings;
- production web build;
- all 25 browser tests, including M6.6 viewport/no-recompute/canonical-identity acceptance;
- Phase18 and Phase21 browser/evidence gates;
- M4 methodology freeze 37/37 and Outcome Engine freeze 4/4.

The candidate is ready to merge after one ledger-bearing final PR validation of this governance
head.

## Merge and canonical-main validation

PR #58 merged with full ancestry as `7679a8eb802124df9dd23058c60603b8c54cb32a`.
Canonical-main workflow `35501699757` / #2402 passed Project OS, M6.5 Source Coverage, mutable
Ruff 0/0, 896 Python tests with zero warnings, the production web build, all 25 browser tests,
Phase18, Phase21, M4 methodology 37/37 and Outcome Engine 4/4.

M6.6 is closed. Viewport interaction remains presentation-only; D-075, Source identity and all
existing freezes remain active. M7 Prospective Evidence Accumulation is the next major task.

## Post-merge closeout correction

Closeout workflow `35501953633` / #2403 on head
`9ceb37152535efa3b70a93358cebc0f63e58527a` passed 895 Python tests and failed one continuity
assertion because `MILESTONES.active` was advanced to M7 while `PROJECT_STATE.current` correctly
remained the closed M6.6 phase. M7 has no activated CR/spec/phase yet.

The correction keeps M6 as the active state-ledger milestone until a formal M7 activation changes
both ledgers atomically. M6 remains complete and M7 remains `ready_not_started`; no product, Source
or freeze semantics change.

Corrected canonical-main workflow `35502065088` / #2404 on head
`7cf6eb947f764c6cc459f496a52276500bd73745` passed 896 Python tests with zero warnings, all 25
browser tests, Phase18/21, Source Coverage, mutable Ruff 0/0 and both M4 freeze guards. The M6.6
closeout is final and M7 remains the next, not-yet-activated task.
