# M3 Phase 3.1 — Real Metadata / Tradability Hardening

## Status

Implementation batch ready on `m3/source-clock-lifecycle-migration`; full GitHub-hosted acceptance remains independent from the current runner-allocation outage.

## Objective

Phase 3.1 closes the gap between a board-level A-share rule profile and the actual tradability state of one security on one session. It remains strictly outside harmonic identity, Source Raw PRZ and source lifecycle ownership.

## Daily-event contract

Optional DuckDB table: `security_daily_event`.

Primary key: `(instrument_id, trade_date)`.

Fields:

- `trading_status`: normalized session state such as `normal`, `suspended`, `resumed`, `special`;
- `no_price_limit`: explicit session-level no-limit flag, nullable when unresolved;
- `price_limit_pct_override`: explicit exceptional percentage, nullable;
- `resolution_complete`: upstream provider certifies whether session-level exception metadata is complete;
- `source` / `reason` / `updated_at` for auditability.

A missing table, missing row or `resolution_complete=false` **never** means that no exception exists. The execution layer must remain fail-safe.

## Resolution order

1. BSE remains deferred.
2. An explicit suspension event makes the session non-tradable and suppresses a usable daily price-limit value.
3. A complete event with `no_price_limit=true` resolves the session as no daily limit.
4. A complete event with `price_limit_pct_override` uses that explicit override.
5. Otherwise the existing security-master/listing-age/risk-warning board profile is used.
6. `special_event_exceptions_unresolved=false` is allowed only when complete daily-event metadata exists for the same `as_of_trade_date`.
7. A stale event from another date is discarded.

No `exact_price_limit_pct` field is introduced. `rule_based_price_limit_pct` remains a rule/context field, not a calculated exchange limit price.

## UI contract

The A-share execution card adds:

- daily trading status;
- tradable / suspended / unresolved state;
- daily-event completeness;
- event source and reason.

The card continues to state that it cannot create, repair or reject harmonic identity or Source Raw PRZ.

## Real-catalog smoke

`scripts/m3_metadata_tradability_smoke.py` automatically:

1. opens `data/market/catalog.duckdb` read-only;
2. counts `security_master` by board;
3. selects representative listed MAIN / STAR / CHINEXT instruments;
4. loads the current security metadata through the production loader;
5. resolves the sample parquet from `daily_dataset` when present;
6. builds the production A-share execution context on the real bars;
7. reports whether `security_daily_event` exists / is populated;
8. writes `artifacts/reports/m3-metadata-tradability-smoke.json`.

Chinese one-click wrapper: `运行M3元数据与可交易性检查.bat`.

The smoke is deliberately non-mutating. Event-table initialization/population belongs to the data-ingestion path, not to analysis reads.

## Deterministic guards

New tests protect:

- complete explicit price-limit override;
- complete suspension -> non-tradable;
- incomplete event cannot clear uncertainty;
- stale-date event cannot be applied;
- optional event table DuckDB round-trip.

## Acceptance boundary

Phase 3.1 is not fully accepted until both are true:

- deterministic Python/Web/browser gates have genuinely executed (not zero-step runner failures);
- the real M1 catalog smoke has produced a machine-readable report from a populated user database.

Neither condition is allowed to block further non-conflicting engineering work while the hosted runner is unavailable.
