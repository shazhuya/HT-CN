# D-085 — M9.4 productizes M7 orchestration but not evidence semantics or calibration authority

status: active
date: 2026-09-22

## Decision

M9.4 turns the established M7 evidence workflow into background product infrastructure without creating a second evidence methodology.

- M9.1 remains the owner of automated market-data readiness. M9.4 consumes its healthy latest-closed-session watermark and does not independently update M1.
- M9.4 may orchestrate the frozen M4 methodology guard, Outcome Engine guard, M7 append precheck, strict QFQ readiness, existing authoritative capture, evidence health, transition report, prospective observation report, existing Outcome v2 and M7 accumulation status.
- M9.4 does not own or reinterpret capture, lifecycle, outcome, Source or harmonic semantics.
- Same-session idempotent no-op skips append-only QFQ/capture/outcome work while refreshing read-only health/transition/observation/accumulation observability.
- Normal daily product operation does not require a clean Git worktree, BAT/PowerShell launch, transport ZIP generation or AI/manual evidence acceptance. Those remain audit/transport tools, not product infrastructure.
- Operational faults and empirical insufficiency are distinct states. A healthy service with ISSUE-0066 open is healthy-but-insufficient, not failed.
- M8 remains fail-closed. Authorization requires ISSUE-0066 closed, zero evidence-chain blockers, non-blocked M7 accumulation and an explicit machine-readable calibration authorization with authorized=true.
- M9.4 does not invent a sample-size threshold and does not expose win-rate, alpha, profitability or statistical-significance values before authorization.

## Failure boundary

A failed guard, failed required capture step, evidence-chain blocker, unreadable/blocked accumulation state, or stale/missing current-cycle report must not advance the background service success watermark. Existing committed evidence remains authoritative and unchanged.

## Non-goals

This decision does not change M4 frozen components, Carney ratios, pivots, Source Raw PRZ, Terminal Price Bar, PEZ, Type-I/Type-II, FIVE_ZERO quarantine, Alternate Bat fail-closed behavior, historical-backfill prohibition or the ban on automatic trading.
