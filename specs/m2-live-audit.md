# M2 Live Visual Audit — first real A-share pass

## Evidence

The first true local-QFQ browser screenshot used `SSE.688256`, returned `420 / 420` real bars for `2024-12-23 -> 2026-09-14`, and showed `0` completed identities plus `30` forming identities before the corrections below.

This screenshot is accepted as real-data evidence because it was generated through the live Playwright path without API fixture interception.

## Findings

### 1. Historical XABC windows were incorrectly kept as "forming"

`iter_forming_xabc_windows` previously returned every historical 4-pivot slice. Once a later confirmed pivot exists, the older XABC is no longer the market frontier and must not remain a live forming candidate.

Correction: forming semantics now use only the latest four confirmed pivots per scale. Historical XABC windows remain available through the generic historical window iterator for research/backtest work.

### 2. Forming projection was checking B but not the already-known C retracement

C exists before D projection. Therefore a source-invalid `C/AB` must reject the forming identity before any PRZ is shown. B-only filtering created too many visually plausible but Carney-invalid projections.

Correction: forming projection now requires both source-backed `B/XA` and `C/AB` constraints before D/PRZ projection.

### 3. Same-node identity conflicts created list noise

Different identities can legitimately share the same XABC/XABCD nodes. They must remain auditable but should not look like independent opportunities.

Correction: API still returns every identity; the UI defaults to the primary (best geometry) identity for each node set and exposes a toggle to reveal alternatives.

### 4. 420-bar overview made the active geometry too small to inspect

Correction: the chart now defaults to a presentation-only focused viewport starting before X and continuing through the latest bar. The full research window remains the engine input and can be restored with the focus toggle.

## Non-goals

These corrections do **not** loosen Carney identity rules and do not transform `geometry_score` into a probability/trading score. They only correct live-candidate lifecycle, source-backed pre-D validation, conflict presentation, and visual audit ergonomics.

## Next calibration gate

After deterministic CI passes, regenerate the live screenshot. Expected qualitative changes:

- forming candidate count should fall sharply;
- each scale contributes at most one live XABC node set;
- C/AB is visible in the forming audit;
- same-node alternate identities are hidden by default but recoverable;
- selected geometry is readable without changing engine input.
