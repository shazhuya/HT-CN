# M9.1 — Automated Market Data & Scheduling Service

status: implementing

## 1. Service boundary

M9.1 adds orchestration around established data components. It MUST NOT redefine market-data normalization, QFQ factor semantics, harmonic Source truth, M4 prospective capture identity, or Outcome Engine behavior.

The service owns only scheduling, process isolation, retry orchestration, health state and user-visible diagnostics.

## 2. Scheduling contract

- Shanghai market time remains authoritative through `latest_closed_trade_clock`.
- The durable service watermark is the latest trading session for which raw update, QFQ readiness and local health all succeeded.
- If the latest closed session is newer than the watermark, one service cycle is due.
- If the watermark already equals or exceeds the latest closed session, the cycle is an idempotent no-op.
- A failed or degraded cycle MUST NOT advance the success watermark and therefore remains automatically retryable.
- Watch mode polls periodically; it does not fabricate a trading day from weekdays alone.

## 3. Data pipeline contract

The initial M9.1 service reuses these existing paths:

1. `scripts/m1_daily_update.py` for calendar-aware incremental raw/delta data update and raw-provider failover.
2. `scripts/m4_prepare_qfq_universe.py` for strict audited QFQ readiness without modifying its frozen semantics.
3. `scripts/m1_health_check.py` for local durable-data consistency checks.

The orchestration layer adds bounded exponential retry around these steps. Provider-specific retry/failover already present below the service remains intact.

## 4. Failure isolation

- Raw market-data update failure blocks QFQ and health for that cycle because downstream freshness cannot be trusted.
- QFQ failure degrades the cycle but does not hide the independent local-health result.
- Any non-healthy cycle leaves the success watermark unchanged.
- An OS advisory lock prevents two service processes from writing the same runtime state concurrently.

## 5. Observability

The service MUST atomically write `data/market/runtime/m9-market-data-service.json` containing:

- service status and health;
- latest target and successful trade dates;
- schedule decision;
- per-step status, exit code and attempt count;
- last-cycle and next-check timestamps;
- provider/calendar provenance when available;
- Chinese diagnostics suitable for the product UI.

Missing/corrupt state must return an explicit non-healthy diagnostic rather than silently reporting success.

## 6. User-computer boundary

Normal daily operation is a long-running application-service responsibility. The user is not required to launch a BAT/PowerShell command for each trading day. Local Private-M1 interaction is exceptional and is not part of M9.1 acceptance.

M9.5 will productize install/start/update/recovery so even initial service startup becomes zero-CLI.

## 7. Acceptance gate

- deterministic tests cover same-session no-op, new-session due, retry recovery, raw failure blocking, degraded QFQ, atomic status and Chinese diagnostics;
- Project OS, source-coverage freeze, Ruff 0/0, Python tests and web build remain green;
- M4 methodology remains 37/37 and Outcome Engine remains 4/4 unchanged;
- hosted validation uses fixtures/mocks and does not require the user's computer or live provider success;
- after candidate validation succeeds, CR-0079 may be activated in Project State and M9.1 may proceed to formal integration.
