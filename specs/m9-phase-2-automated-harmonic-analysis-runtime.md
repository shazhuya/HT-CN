# M9.2 — Automated Harmonic Analysis Runtime

status: ready_to_merge

## 1. Objective

Make harmonic analysis a continuously maintained product runtime rather than an API-request side effect. New canonical bars must advance a controlled product-analysis snapshot automatically while all frozen Source semantics remain owned by the existing harmonic service.

## 2. Architecture

M9.2 adds an orchestration layer around established components:

1. M9.1 owns market-data/session readiness.
2. OperatorCacheInputIdentity binds finalized market inputs and analysis-code identity.
3. M3SourceClockHarmonicService remains the product harmonic/lifecycle adapter.
4. build_or_load_operator_snapshot remains the only product-universe scan/cache primitive and keeps its process-local single-flight plus filesystem cache-slot lock.
5. the new M9.2 runtime owns only scheduling, watermark, retries, health and provenance.
6. the production API exposes read-only M9.2 runtime status.

No second scanner, lifecycle engine, PRZ engine, cache truth or empirical ranking layer may be introduced.

## 3. Trigger and watermark contract

The runtime evaluates a tuple of:

- target closed trade date;
- data-input fingerprint;
- analysis-code fingerprint;
- combined input-identity fingerprint.

A cycle is due when:

- a new canonical closed session exists;
- finalized canonical input changes within the same session;
- the operator explicitly forces one bounded refresh; or
- the previous cycle was degraded/failed and therefore did not advance the success watermark.

An exact same-session/same-input identity is an idempotent no-op.

Only a fully current, single-as-of snapshot with stable input identity and zero failed instruments advances last_success_trade_date and last_success_input_identity_fingerprint. Degraded cycles remain observable and retryable.

## 4. Source and lifecycle provenance

Every successful/degraded cycle records product provenance that states:

- Source truth comes from the existing M3SourceClockHarmonicService / Source lifecycle / decision-narrative stack;
- viewport inputs are absent;
- viewport state cannot trigger analysis;
- the runtime does not synthesize future nodes;
- the runtime does not mutate harmonic identity or Source Raw PRZ;
- the runtime does not own lifecycle;
- the runtime is not authoritative M4 evidence and writes no M4 evidence.

The runtime must fail closed if the operator snapshot contract claims any forbidden ownership/mutation.

## 5. Viewport independence

M6.6 remains authoritative for chart-coordinate behavior. M9.2 accepts only canonical data/code identity, universe, bars and scan scales. Pan, zoom, crosshair, selected pattern and visual focus are presentation state and are intentionally absent from the runtime schedule/provenance inputs.

Existing M6.6 browser acceptance remains required at formal PR release gates.

## 6. Forming-pattern / future-node rule

M9.2 never constructs harmonic points. It calls the existing Source-aligned service and transports its current pattern/lifecycle observations into the existing operator snapshot. Therefore:

- missing/future nodes are never invented by the runtime;
- Shark remains 0XABC with no fabricated D;
- forming patterns evolve only after canonical bars change the underlying observed analysis;
- lifecycle remains Source-clock-owned.

Any future implementation that creates points inside the runtime requires a new Change and Source decision and is outside this phase.

## 7. Failure and retry behavior

- missing catalog or empty initialized universe: fail closed;
- unresolved canonical trade date: fail closed;
- input-identity construction failure: fail closed;
- stale/mixed-as-of snapshot: fail closed;
- input identity changing during build: fail closed;
- one or more instrument analysis failures: degraded, do not advance the success watermark, retry automatically;
- runtime status is written atomically with Chinese diagnostics;
- a process lock prevents duplicate long-running runtime instances.

No failure may mutate frozen methodology or authoritative evidence.

## 8. Product API

Add GET /api/harmonic/runtime/status.

It is read-only and exposes:

- service status / health;
- target and last-success watermarks;
- schedule reason;
- current cycle summary;
- input/provenance contract;
- Chinese diagnostics.

The endpoint must be declared before the dynamic /api/harmonic/{instrument_id} route so runtime/status is never interpreted as an instrument id.

## 9. Tests

Hosted tests must cover at least:

- same-session/same-input idempotent no-op;
- new-session trigger;
- same-session canonical-input-change trigger;
- provenance has no viewport inputs and no Source ownership/mutation;
- degraded per-instrument failure remains retry-required;
- input identity change during build fails closed;
- forbidden identity-mutation queue contract fails closed;
- atomic status round-trip with Chinese diagnostics;
- status API before first run and with persisted provenance.

Formal PR validation must additionally keep Project OS, Source Coverage, Ruff 0/0, all Python tests / 0 warnings, Web build, existing browser acceptance, Phase18, Phase21, M4 methodology frozen_match_37 and Outcome Engine frozen_match_4 green.

## 10. Exit gate

M9.2 may close when:

- new canonical bars automatically trigger a controlled incremental product-universe harmonic refresh;
- exact same canonical input is idempotent;
- forming/lifecycle state remains exclusively Source-service-owned with no fabricated future nodes;
- viewport interaction remains outside analysis identity;
- runtime provenance/status is auditable and Chinese-diagnostic-visible;
- no routine user-computer action is required;
- formal PR and canonical-main release gates are green.
