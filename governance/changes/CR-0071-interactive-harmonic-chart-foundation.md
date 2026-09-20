# CR-0071 — M6.6 Interactive Harmonic Chart Foundation

status: implementing
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
