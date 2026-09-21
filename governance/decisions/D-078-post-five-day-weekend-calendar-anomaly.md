# D-078 — Post-five-day weekend raw rows are audited legacy calendar anomalies

status: active
date: 2026-09-21

## Decision

For SZSE QFQ readiness, raw rows dated on Saturday or Sunday on or after 1992-01-01 are not treated as evidence of a formal trading session. The Shenzhen Stock Exchange's official 1992 chronology states that the exchange began a five-day trading week on 1992-01-01.

These rows may receive a synthetic compatibility factor only when the entire missing run is strictly outside the frozen 420-bar formal prospective-capture window. The raw OHLCV row itself is never deleted, rewritten, or used to alter current harmonic geometry.

Pre-1992 Saturday handling remains governed by D-077. Current/formal-window gaps remain fail-closed.

## Evidence

- Shenzhen Stock Exchange, 1992 chronology: https://www.szse.cn/aboutus/sse/events/t20070328_497826.html
  - 1992-01-01: the exchange began a five-day trading week.
- Third real M7 bundle on canonical main `c1be51ef099c11bb5addbb9e501fc195fad433e4` exposed provider factor gaps at 1992-02-01, 1992-02-02 and 1993-01-03 for SZSE.000001.
- Those dates are weekend dates and therefore post-date the documented five-day-week boundary.

## Boundaries

This is a mutable QFQ preparation/control-plane rule. It does not modify the frozen 37-component M4 capture methodology, the 4-component Outcome Engine, Source semantics, harmonic geometry, lifecycle semantics, or the statistical-inference boundary.

D-078 refines the calendar classification used alongside D-077; it does not relax D-077's requirement that any exceptional bridge remain outside the frozen 420-bar formal window.
