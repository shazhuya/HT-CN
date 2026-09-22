# CR-0079 — M9.1 Automated Market Data & Scheduling Service

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 669d41fccc37a1f4acc1a9591793bc41c985c15f
target: main
milestone: M9.1

## Trigger

M9.0 made productization the development mainline and explicitly prohibited routine daily user-computer/BAT/ZIP operation as project infrastructure. Existing M1/M2/M4 components already provide market calendar resolution, tail-increment A-share updates, provider failover, adjusted-history retry, strict QFQ readiness and local data health, but normal operation still depends on manually launching scripts.

## Objective

1. Add one long-running, idempotent market-data service that schedules work from the latest closed A-share trading session.
2. Reuse existing validated M1 data update and strict QFQ paths rather than rewriting data semantics.
3. Add step-level retry/backoff around the existing provider-level failover/retry boundaries.
4. Persist machine-readable service health and Chinese diagnostics atomically.
5. Prevent overlapping service instances with an OS advisory lock.
6. Make a same-session rerun a successful no-op and keep failed/degraded sessions eligible for automatic retry.
7. Expose service state to the application without introducing trading execution or changing harmonic Source identity.

## Non-goals

- no change to harmonic detection, Source Raw PRZ, lifecycle or execution semantics;
- no change to frozen M4 capture methodology or Outcome Engine;
- no statistical win-rate/alpha/profitability claims;
- no 5-0 or Alternate Bat production changes;
- no automatic order placement;
- no user-machine Private-M1 dependency for hosted validation.

## Acceptance

See `specs/m9-phase-1-automated-market-data-scheduling-service.md`.


## Closeout

PR #67 merged with ancestry preserved as `ecfdd3116c358c60359f917752b6d06aedefc065`. Final ledger-bearing PR workflow `35688064505` / `#2488` and canonical-main workflow `35688218646` / `#2489` both passed deterministic and formal main-release gates with 940 Python tests / 0 warnings, 25 browser tests, Phase18/21, M4 methodology frozen_match_37 and Outcome Engine frozen_match_4. M9.1 is closed and M9.2 becomes the next productization task.
