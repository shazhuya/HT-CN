# CR-0071 — M6.6 Interactive Harmonic Chart Foundation

status: planned
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
