# M3 Phase 3.1 — Daily Trading Event Ingestion

## Purpose

This batch turns the Phase-3.1 daily-event contract into an automated evidence pipeline without pretending that one public feed is an exhaustive exchange-rule source.

## Source boundary

The initial ingestion uses AKShare `stock_tfp_em` / Eastmoney suspension data only as **positive suspension evidence**.

- a returned continuous/daily suspension becomes `trading_status=suspended`;
- a returned intraday suspension becomes `trading_status=intraday_suspended`;
- rows outside the requested session are filtered even if the upstream endpoint returns historical records;
- every record remains `resolution_complete=false`;
- an empty successful response creates no synthetic `normal` rows;
- therefore absence from the source never means that all special price-limit/resumption/security-event exceptions are resolved.

## Non-downgrade storage

`security_daily_event` keeps the strongest known record for one `(instrument_id, trade_date)`. A later partial event cannot overwrite an existing `resolution_complete=true` record. This allows future exchange-grade or second-source event feeds to coexist safely with current positive-only evidence.

## Sync audit

`security_daily_event_sync` records whether a source was actually queried, whether it succeeded, record count and `coverage_scope`.

Current source scope is `positive_evidence_only`. This lets the product distinguish:

- no sync attempted / failed: `event_unknown`;
- source queried successfully but only positive-event coverage exists: `event_partial`;
- explicit suspension row exists: `confirmed_suspended` (or intraday suspension);
- a future authoritative complete source may emit `event_complete`.

## Product boundary

This ingestion does not modify harmonic identity, Source Raw PRZ, lifecycle ownership, Type-I/Type-II semantics, RSI BAMM, or any frozen M2.31 research result.
