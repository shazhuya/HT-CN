# CR-0071 — M6.6 Interactive Harmonic Chart Foundation

status: implementing
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.6

## Objective

Build the TradingView-class interactive chart/coordinate foundation required by D-069 before M7.

## First implementation slice

- production K-line renderer moves to lightweight-charts v5;
- harmonic points/legs become canonical trade_date+price overlays;
- existing Source PRZ/PEZ/T1/T2/events are mapped through the same coordinate APIs;
- crosshair OHLC/node readout;
- viewport transform synchronization and reset;
- browser regression for pan/zoom alignment and future-node non-fabrication.

## Source boundaries

This change may not modify M2/M3/M4 harmonic identity, Source Raw PRZ, Source Clock,
Reaction/Reversal, 5-0 quarantine, Alternate Bat fail-closed state or prospective evidence.


## Activation evidence

Hosted branch workflow `35487588566` / #2384 on head
`158d6cd3b316dc5f847d06fd0ff95a0e223e19c3` passed:

- Project OS v2 integrity;
- M6.5 Source Coverage freeze verifier;
- mutable Ruff 0 / budget 0;
- Python 896 passed;
- pytest warnings 0;
- Web TypeScript/Vite build success.

The first implementation slice is therefore activated. PR-only browser interaction,
Phase18/Phase21 and immutable M4 freeze gates remain required before promotion.


## First PR browser finding

PR #59 workflow `35487667066` / #2386 kept all existing browser semantics green
(24 legacy browser tests passed) but the two new M6.6 interaction tests exposed unstable test targeting:

1. wheel zoom around the D anchor can legitimately leave D's screen X unchanged;
2. a generic center-screen mouse position is not guaranteed to map to a candle and may yield no
   crosshair series datum.

The implementation is therefore kept in `implementing`. The next candidate uses deterministic
viewport zoom controls, verifies real drag-pan separately, and targets crosshair at the canonical
D-node time coordinate. No Source or M4 semantics are changed.
