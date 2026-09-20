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
