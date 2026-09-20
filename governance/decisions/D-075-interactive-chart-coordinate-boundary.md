# D-075 — Interactive chart engine owns viewport coordinates, never harmonic Source truth

status: `active`

## Decision

M6.6 replaces the production deep-dive chart's fixed hand-calculated SVG candle coordinate system
with a TradingView Lightweight Charts time/price viewport plus an HT-CN-owned overlay layer.

The boundary is strict:

1. canonical HT-CN bars keep `index + trade_date + OHLC` identity;
2. harmonic points/lifecycle objects keep their canonical Source-derived index/time/price identity;
3. Lightweight Charts owns only viewport interaction and conversion between canonical time/price
   and screen coordinates;
4. HT-CN overlays use `timeToCoordinate` and `priceToCoordinate` (or equivalent stable APIs)
   to render the already-computed Source/product objects;
5. pan, zoom, price-axis movement, resize and crosshair movement never trigger harmonic
   identification or mutate Source Identity / Raw PRZ / Source Clock / lifecycle state;
6. new market data, a changed analysis window, symbol or analysis parameters may trigger controlled
   analysis/data updates separately from viewport interaction.

## Initial renderer

The production React chart uses:

- Lightweight Charts candlesticks for A-share bars;
- an absolute HT-CN SVG overlay for observed harmonic nodes/legs and price/lifecycle layers;
- one shared time/price coordinate adapter;
- crosshair identity readout backed by the same canonical bar identity;
- TradingView attribution logo left enabled.

The overlay may evolve to chart primitives later, but the Source/viewport ownership boundary above
must remain unchanged.

## No-fabrication rule

A forming topology renders only points that actually exist in `pattern.points`. In particular,
Shark remains `0-X-A-B-C` and never acquires a synthetic D from the chart renderer.

## Verification

Browser acceptance must prove that viewport changes redraw overlays while the harmonic analysis
request count does not increase, and that a crosshair placed at a rendered node resolves to the
same canonical trade date after viewport changes.
