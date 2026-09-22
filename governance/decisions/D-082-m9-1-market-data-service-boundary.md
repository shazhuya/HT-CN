# D-082 — M9.1 uses an idempotent service watermark over established data/QFQ primitives

status: active
date: 2026-09-22

## Decision

M9.1 does not create a second market-data or QFQ truth. It wraps the established M1/M4 data paths with a product-level service boundary.

- Shanghai closed-session resolution remains owned by `latest_closed_trade_clock`.
- Incremental raw/delta A-share update remains owned by the established M1 daily updater and its provider failover.
- Strict QFQ readiness reuses the existing audited QFQ path; frozen M4 semantics are not rewritten.
- The M9.1 service owns scheduling, step retry/backoff, process isolation, a successful-trade-date watermark, atomic status persistence and Chinese diagnostics.
- The success watermark advances only when raw update, QFQ readiness and local health all pass.
- Same-session service checks are idempotent no-ops; degraded/failed cycles remain retryable.
- Normal daily operation must not require a new BAT/PowerShell invocation or Private-M1 handoff.

## Why

The project already has validated low-level data primitives. Reimplementing them inside productization would create semantic drift and risk changing frozen research behavior. A thin orchestration service converts those primitives from supervised scripts into continuous product infrastructure while retaining their existing provenance and fail-closed behavior.

## Boundary

This decision does not change harmonic Source identity, Raw PRZ, lifecycle, M4 capture methodology, Outcome Engine, ISSUE-0066 inference restrictions, FIVE_ZERO quarantine, Alternate Bat fail-closed status, or the prohibition on automatic trading.

M9.5 remains responsible for packaging/install/start/update/recovery so initial service startup itself becomes zero-CLI.
