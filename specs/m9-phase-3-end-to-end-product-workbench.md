# M9.3 — End-to-End Product Workbench

status: ready_to_merge

## 1. Objective

Deliver the first coherent HT-CN product surface where a user can move from market/runtime readiness to symbol selection, canonical candlesticks, harmonic geometry, Source lifecycle and Chinese next-observation guidance without switching mental models or manually stitching together separate tools.

## 2. Product workflow

The normal research flow is:

1. see automated market-data and harmonic-runtime readiness;
2. select a symbol directly or from Operator Queue;
3. enter the single-instrument workbench without a second manual handoff;
4. inspect canonical QFQ candles;
5. inspect the selected primary harmonic identity and optional same-node identity conflicts;
6. inspect ratios, HT-CN core, component envelope and Source Raw PRZ separately;
7. inspect Source lifecycle events, PEZ, T-Bar, T+1 and T1/T2 when available;
8. read the Chinese action-state narrative: now / first watch / next watch / upgrade blocker;
9. move crosshair to any canonical bar and see the exact same date/OHLC/node/lifecycle identity in the adjacent context panel;
10. pan/zoom/focus/select candidates without causing a harmonic API recomputation.

## 3. Runtime integration

M9.3 reads M9.1 and M9.2 status endpoints and presents their watermarks in the UI.

These are observability signals only. The workbench must not become the scheduler or analysis owner.

## 4. Canonical identity sharing

HarmonicChart owns chart rendering only. It may publish a read-only CrosshairSnapshot containing:

- trade date;
- OHLCV;
- harmonic node labels at that bar;
- Source lifecycle event labels at that bar.

The adjacent WorkbenchContextPanel consumes the same snapshot. It must never infer or create a new harmonic identity from pointer coordinates.

## 5. Decision-support panel

For the selected primary identity, the integrated context must show:

- pattern/schema/scale/direction;
- lifecycle state;
- frozen Source PRZ or explicit fail-closed state;
- next key price and role;
- source-aligned or retrospective T1/T2 with explicit clock semantics;
- principal ratio measurements;
- canonical crosshair/latest-bar context.

The existing DecisionNarrative remains the source of the Chinese now / first watch / next watch / upgrade blocker wording. M9.3 may compose it but must not independently redefine lifecycle.

## 6. Interaction behavior

- Enter in the symbol field starts analysis.
- Selecting an Operator Queue instrument starts deep analysis for that exact instrument.
- Candidate selection changes only presentation focus.
- focus toggle, pan, zoom, reset and crosshair do not rerun the harmonic API.
- chart overlay coordinates continue to derive from canonical bar/time/price identity.
- missing Source evidence remains visibly fail closed.

## 7. Browser acceptance

A dedicated M9.3 Playwright scenario must verify:

- runtime readiness cards render;
- keyboard symbol selection opens the end-to-end workbench;
- Chinese DecisionNarrative is present;
- selected identity, lifecycle, Source PRZ, next key price, targets and ratios are visible together;
- the D-node canonical trade date is preserved;
- moving crosshair to D updates the adjacent context panel with the same date and node;
- zoom changes viewport version while harmonic request count stays unchanged.

All existing browser suites remain mandatory at formal PR gates.

## 8. Non-goals

M9.3 does not implement background evidence automation (M9.4), packaging/zero-CLI startup (M9.5), stable release acceptance (M9.6), statistical calibration, trading execution or any new Carney methodology.

## 9. Exit gate

M9.3 may close only when:

- symbol selection, candles, overlays, ratios, PRZ, targets and lifecycle are visibly integrated;
- Chinese decision support explains current state and next observation points;
- crosshair/hover and adjacent information panels share canonical bar/time/price identity;
- the dedicated end-to-end browser workflow passes;
- existing M6.6 browser behavior and immutable M4/Outcome freeze guards remain green;
- normal validation requires no user-computer action.
