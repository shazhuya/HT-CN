# D-083 — M9.2 reuses canonical operator snapshot identity; viewport is never an analysis trigger

status: active
date: 2026-09-22

## Decision

M9.2 automates product harmonic analysis by orchestrating the already-established Source-aligned service and operator snapshot cache. It does not create a second harmonic scanner, lifecycle engine, PRZ truth or product cache truth.

- The runtime watermark is derived from the latest canonical closed trade date plus the established data/analysis-code input identity.
- Exact same-session/same-input checks are idempotent no-ops.
- A new canonical session or changed finalized canonical input triggers a controlled product-universe refresh.
- Degraded or failed cycles do not advance the success watermark and remain retryable.
- `M3SourceClockHarmonicService` remains the product Source/lifecycle adapter.
- `build_or_load_operator_snapshot` remains the product-universe scan/cache primitive, including its single-flight, cross-process lock and input-stability checks.
- Viewport state, pan, zoom, crosshair, selected pattern and visual focus are presentation-only. They are not runtime inputs and can never trigger harmonic identity recomputation.
- M9.2 never constructs harmonic nodes. Missing/future nodes cannot be synthesized by this runtime.
- M9.2 does not own lifecycle, mutate harmonic identity, mutate Source Raw PRZ, produce trade instructions, or write authoritative M4 evidence.

## Why

M6.6 already established the canonical separation between data/harmonic state and viewport coordinates. M5 already established a concurrency-safe, input-identity-bound product snapshot. Reusing those boundaries gives M9.2 automation without semantic duplication or Source drift.

## Failure boundary

The runtime fails closed on stale/mixed-as-of snapshots, input identity changes during a build, forbidden queue ownership/mutation claims, missing canonical data, or unresolved target trade date. Per-instrument failures produce a degraded retryable cycle and do not advance the success watermark.

## Non-goals

This decision does not change Carney ratios, Source Raw PRZ, Terminal Price Bar, PEZ, Type-I/Type-II, FIVE_ZERO quarantine, Alternate Bat fail-closed state, HSI/RSI-BAMM-acceleration support, M4 methodology, Outcome Engine, ISSUE-0066 inference restrictions, or the prohibition on automatic trading.
