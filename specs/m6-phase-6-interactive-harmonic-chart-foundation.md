# M6.6 — Interactive Harmonic Chart Foundation

status: ready_to_merge

## 1. Objective

Upgrade the production single-instrument chart from a fixed SVG snapshot to a TradingView-class
interactive research chart while preserving all frozen HT-CN Source semantics.

## 2. Fixed architecture

The chart has three separate responsibilities:

1. **canonical data / harmonic state** — supplied by HT-CN analysis payloads;
2. **interactive viewport** — Lightweight Charts pan/zoom/time/price axes/crosshair;
3. **HT-CN overlay projection** — maps canonical time + price into screen coordinates.

Viewport state is presentation state only. It must never become harmonic identity state.

## 3. Phase order

### Phase A — interactive candle/coordinate foundation

- production candlesticks use Lightweight Charts;
- A-share visual convention remains red-up / green-down;
- time axis, price axis, wheel zoom, drag pan, axis scaling, auto resize and reset/focus work;
- chart coordinate adapter maps `trade_date -> x` and `price -> y`;
- pan/zoom/resize redraw overlay without a new `/api/harmonic` request;
- default TradingView attribution remains visible.

### Phase B — topology overlays

- XABCD, ABCD and 0XABC observed nodes and legs use the shared coordinate adapter;
- node labels include observed price;
- forming patterns never render future/missing nodes;
- Shark never renders D;
- pattern selection/focus changes viewport only and does not alter identity.

### Phase C — price zones and Source lifecycle

The same adapter renders:

- HT-CN Ideal Core;
- Component Envelope;
- Source Raw PRZ;
- PEZ;
- T1/T2;
- Source Terminal / T+1;
- Type-I / Type-II lifecycle events.

No display layer may be relabeled as Source Raw PRZ.

### Phase D — crosshair and data-driven updates

- crosshair resolves canonical trade date and OHLC;
- if the crosshair bar hosts harmonic nodes/lifecycle events, the readout exposes the same identity;
- new bars or analysis payload changes update data/overlay through controlled recomputation;
- viewport interaction alone never re-runs analysis.

## 4. Initial implementation acceptance

The first M6.6 candidate must already provide:

- interactive Lightweight Charts candlesticks in the production deep-dive;
- observed harmonic node/leg overlay anchored by canonical time + price;
- existing Ideal Core / Envelope / Source PRZ / PEZ / Type-I target / lifecycle overlays migrated to
  the shared adapter when their payload data exists;
- reset/focus behavior;
- crosshair OHLC + node/lifecycle identity;
- Playwright proof that viewport interaction does not increase harmonic API request count;
- Playwright proof that overlay identity remains tied to the same trade date after viewport change;
- existing M5 portable evidence renderer left intact as a regression/evidence path.

## 5. Source and research non-goals

M6.6 must not change:

- Carney pattern ratios or identity;
- Source Raw PRZ membership;
- Terminal Price Bar / PEZ / Type-I / Type-II definitions;
- 5-0 quarantine or Alternate Bat fail-closed state;
- RSI BAMM semantics;
- M4 methodology/outcome freezes;
- A-share universe coverage;
- trading execution behavior.

## 6. Exit gate

M6.6 closes only after the production main chart no longer depends on a fixed SVG candle snapshot,
all current harmonic/price/lifecycle overlays share canonical time/price coordinates, browser tests
cover pan/zoom/crosshair/resize/data update/no-recompute semantics, PR + canonical main gates are
green, and M7 becomes the next major task.
