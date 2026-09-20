# M6.6 — Interactive Harmonic Chart Foundation

status: implementing

## 1. Objective

Replace the production single-instrument chart's fixed-SVG candle coordinate system with a
TradingView-class interactive chart foundation while preserving HT-CN harmonic Source truth
outside the chart library.

## 2. Architectural boundary

- `lightweight-charts` owns candlestick rendering, time/price scales, pan, zoom and crosshair.
- HT-CN canonical bars/pattern/lifecycle payloads remain authoritative.
- Harmonic overlay coordinates are derived from canonical `trade_date + price` anchors through
  chart time/price coordinate APIs.
- viewport transforms never call the harmonic API and never mutate identity, Raw PRZ or lifecycle.
- data/pattern prop changes may rebuild/recompute the view; mouse pan/zoom only recomputes pixels.

## 3. Phase A — interactive candlestick and harmonic coordinate foundation

1. Render production candlesticks with lightweight-charts v5.
2. Support horizontal pan, wheel/pinch zoom, price/time scale interaction and viewport reset.
3. Render XABCD / ABCD / 0XABC observed nodes and legs in an independent SVG overlay using the
   same chart time/price coordinate system.
4. Never synthesize missing future nodes.
5. Expose crosshair OHLC and harmonic node identity from the same canonical date.
6. Recompute overlay pixel coordinates on viewport/resize interaction without re-running analysis.

## 4. Phase B — Source zones and lifecycle overlays

Migrate Source Raw PRZ, Ideal Core, Component Envelope, PEZ, T1/T2, Source Terminal, T+1 and
Type-I/Type-II events onto the same coordinate mapping. Phase A may carry the existing source
PRZ/PEZ/T1/T2/event subset as compatibility overlays while the complete layer set is migrated.

## 5. Browser acceptance

Automated browser tests must prove:

- chart engine is interactive and production-bound;
- an observed harmonic node moves in screen coordinates after zoom/pan;
- the corresponding Source PRZ/event overlay moves under the same viewport transform;
- node identity/index/price attributes remain unchanged;
- reset returns a valid aligned view;
- crosshair reports OHLC and node identity;
- forming XABCD/Shark do not render missing D/C.

## 6. Non-goals

No harmonic ratio changes, no Source Raw PRZ changes, no M4 methodology/outcome mutation, no
trading execution, no TradingView script editor or social/drawing-tool clone.

## 7. Exit gate

M6.6 closes only after all Blueprint M6.6 gates pass and canonical main is post-merge green.
