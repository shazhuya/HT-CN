# D-075 — Chart engine owns viewport coordinates, never harmonic Source truth

status: `active`

## Decision

M6.6 uses `lightweight-charts` as the production candlestick/time-price interaction engine.
HT-CN harmonic nodes, PRZs and lifecycle events remain canonical data outside the library.

Every overlay anchor is expressed as canonical `trade_date/index + price`. Pixel coordinates are
derived from the chart's time scale and candlestick series price scale whenever the viewport changes.

## Consequences

- pan/zoom/axis scaling recomputes overlay pixels only;
- viewport input must not call the harmonic analysis API;
- new bars, symbol/parameter changes or a new analysis payload may trigger controlled recomputation;
- future pattern nodes are never fabricated for visual completeness;
- a chart-library upgrade cannot redefine Source Identity, Raw PRZ or Source Clock.
