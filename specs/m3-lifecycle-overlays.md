# M3 Phase 2 — Lifecycle chart overlays

Date: 2026-09-16

## Goal

Make the Phase-1 lifecycle navigator spatially consistent with the K-line chart. A trader should not have to read a target in a text card and mentally reconstruct where that target sits relative to PRZ and current price.

## Type-I target overlays

When the selected completed pattern has an existing M2 `reaction_audit`, draw:

- `T1 38.2%` from `reaction_audit.target_382`;
- `T2 61.8%` from `reaction_audit.target_618`.

The overlay begins at the audited D/Terminal index and extends through the latest visible bar.

Each target exposes two states only:

- `pending` when the matching `bars_to_*` field is null;
- `reached` when the matching `bars_to_*` field is non-null.

The target label must include its price and Chinese state text (`已到达` / `待到达`).

## Chart-scale rule

T1/T2 prices participate in the visible price extent whenever they are rendered. The chart must not silently place a lifecycle target outside the viewport.

## Scientific boundary

These lines visualize existing M2 lifecycle evidence only. They:

- do not alter XABCD/ABCD/0XABC/5-0 identity;
- do not alter PRZ geometry;
- do not infer a new target from current price;
- do not convert historical group evidence into a current-symbol probability;
- do not create a buy/sell/add/reduce instruction.

Forming candidates without `reaction_audit` do not show Type-I target overlays.

## Acceptance

Automated browser regression must verify at least:

1. forming state has no T1/T2 overlays;
2. T1-reached state renders T1=`reached`, T2=`pending`;
3. T2-reached state renders both as `reached`;
4. Type-II state preserves both Type-I target histories as reached when the source audit says so;
5. target price and Chinese reached/pending label are visible in the SVG.
