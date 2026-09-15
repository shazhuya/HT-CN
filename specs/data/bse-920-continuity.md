# BSE 920 code continuity strategy

## Status

M1 full-market daily initialization currently processes SSE and SZSE first and defers BSE.
This is intentional, not a permanent exclusion.

## Why BSE is deferred

The Beijing Stock Exchange migrated existing listed-company securities to the `920xxx` code
range in 2025. Historical data providers do not all expose pre-migration and post-migration
history as one continuous series under the new code. Some fallback providers also only
recognize Shanghai/Shenzhen provider-code prefixes.

Naively treating `BSE.920xxx` as if it had always existed risks one of two failures:

1. provider errors / empty history;
2. a truncated post-migration series that silently loses earlier history.

The second failure is more dangerous for HT-CN because harmonic pivots, ratios, PRZs and
backtests depend on continuous historical bars.

## Required adapter before BSE activation

The dedicated BSE continuity adapter must:

- ingest the official old-code -> new `920xxx` mapping;
- resolve provider-specific symbols for both sides of the migration;
- fetch pre-switch and post-switch daily history separately when needed;
- normalize OHLCV units to the HT-CN canonical schema;
- stitch the two ranges by trade date without duplicate bars;
- preserve provenance for each segment;
- cross-check representative securities against a second source;
- include regression tests spanning the migration date.

Only after these checks pass should BSE securities enter the same full-market initializer as
SSE/SZSE.
