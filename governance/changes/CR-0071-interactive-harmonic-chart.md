# CR-0071 — M6.6 Interactive Harmonic Chart Foundation

status: planned
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
