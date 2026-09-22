# D-084 — M9.3 shares canonical hover identity across panels but presentation never owns analysis

status: active
date: 2026-09-22

## Decision

M9.3 composes the established HT-CN product capabilities into one workbench without creating a new analysis truth.

- The chart may publish a read-only crosshair snapshot containing canonical trade date, OHLCV, harmonic node labels and Source lifecycle event labels for the pointed bar.
- The adjacent workbench context panel consumes exactly that snapshot and the already-selected harmonic identity.
- Pointer coordinates, pan, zoom, focus, crosshair and candidate selection remain presentation state. They never enter the harmonic input identity, never trigger Source recomputation and never create or mutate harmonic nodes.
- M9.1 market-data status and M9.2 harmonic-runtime status are displayed as observability only; M9.3 does not become a scheduler or runtime owner.
- The existing DecisionNarrative remains the owner of Chinese now / first watch / next watch / upgrade-blocker wording.
- Source Raw PRZ, PEZ, Terminal Price Bar, T+1 and Type-I/Type-II lifecycle remain owned by the established Source-aligned service.

## Why

The user needs one coherent product surface, but combining panels must not collapse the architectural separation established in M3, M6.6 and M9.2. A shared canonical read-only identity lets chart, hover and information panels agree without turning the viewport into analysis state.

## Failure boundary

If a canonical bar/node/lifecycle identity is unavailable, the UI shows an explicit empty/latest-bar context. It must never infer a missing harmonic point from screen coordinates or silently substitute HT-CN core/component envelope for unresolved Source Raw PRZ.

## Non-goals

This decision does not change Carney ratios, pivots, pattern identity, FIVE_ZERO quarantine, Alternate Bat fail-closed behavior, M4 methodology, Outcome Engine, ISSUE-0066 inference restrictions, M7/M8 boundaries, or the prohibition on automatic trading.
