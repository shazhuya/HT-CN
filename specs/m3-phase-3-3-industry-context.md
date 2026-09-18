# M3 Phase 3.3 — Industry / Relative-Strength Context

## Objective

Add an auditable industry layer between the individual security and the four core market benchmarks without allowing sector information to repair or redefine harmonic identity.

## Membership source

The initial production mapping uses AKShare's Eastmoney industry interfaces:

- `stock_board_industry_name_em`
- `stock_board_industry_cons_em`

Refresh is all-or-nothing: every industry and constituent set is fetched before the prior mapping is replaced. Any board failure preserves the previous complete mapping.

If one security maps to multiple industries from the same source, HT-CN returns `membership_ambiguous` and refuses to choose automatically.

## Strength / breadth source

Eastmoney supplies membership only. HT-CN recomputes industry evidence from local M1 constituent bars:

- 1 / 5 / 20-session compounded constituent returns;
- equal-weight mean and median return;
- percentage of calculable members above MA20;
- one-day up/down breadth;
- average constituent 20-session volume ratio.

This is a transparent local aggregate, not an Eastmoney industry index and not a proprietary score.

## Evidence hierarchy

`individual -> industry -> STAR50 / ChiNext / CSI300 / SSE Composite`

Industry context is evidence-only:

- `mutates_harmonic_identity=false`
- `mutates_source_raw_prz=false`
- `owns_lifecycle=false`

## Sync

`scripts/m3_sync_industry_context.py` refreshes membership only when the last successful mapping is older than seven days by default, then rebuilds the latest industry snapshot from local M1 data.

One-click wrapper: `运行M3行业环境同步.bat`.
