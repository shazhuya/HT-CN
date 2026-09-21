# D-080 — No new closed session means no append-only work; missed sessions fail closed

status: active
date: 2026-09-21

## Decision

After M1 updates the local market clock, M7 must decide whether a new authoritative append is actually due before running strict QFQ preparation, lifecycle capture, or outcome snapshot generation.

- latest closed trade date == latest committed capture date: successful `idempotent_noop`; do not rerun append-only QFQ/capture/outcome work;
- exactly one closed trade date is newer than the latest committed capture: `capture_due`; preserve the existing strict 55/55 QFQ gate and frozen capture/outcome semantics;
- more than one closed trade date is newer than the latest committed capture: fail closed as `missed_closed_sessions_no_backfill_allowed`;
- committed evidence ahead of or absent from the local trade calendar: fail closed.

A missing current-run QFQ report is acceptable to M7 intake only for a verified `idempotent_noop` whose precheck proves pending_closed_trade_count=0 and latest_closed_trade_date equals latest_committed_capture_date.

## Boundaries

This changes only mutable M7 operational control and transport packaging. It does not alter M1 data, raw OHLCV, the frozen 37-component M4 capture methodology, the 4-component Outcome Engine, Source semantics, enrollment, lifecycle, or ISSUE-0066 inference boundaries.
