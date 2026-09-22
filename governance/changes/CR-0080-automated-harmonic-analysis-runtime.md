# CR-0080 — M9.2 Automated Harmonic Analysis Runtime

status: implementing
baseline_ref: main
baseline_head: 34396aec87c589aae7a981fc029bc3e81f82f64d
implementation_baseline_head: 34396aec87c589aae7a981fc029bc3e81f82f64d
work_branch: m9/automated-harmonic-analysis-runtime-v1
phase: M9.2

## Objective

Promote the existing deterministic HT-CN harmonic service and operator snapshot cache into an automated product runtime that reacts to new canonical market-data identity without creating a second harmonic truth.

## Scope

- observe the canonical local market-data/session watermark produced by M9.1;
- build a canonical data + analysis-code input identity;
- trigger a controlled all-initialized-universe harmonic refresh when the closed-session or input identity changes;
- reuse the existing operator snapshot single-flight, cross-process cache lock, Source lifecycle and decision-narrative stack;
- persist runtime watermark, health, Chinese diagnostics and auditable provenance;
- expose runtime status through the product API.

## Fixed boundaries

- no Carney ratio, identity, pivot, Source Raw PRZ, Terminal Price Bar, PEZ, Type-I or Type-II semantic changes;
- no fabricated future nodes;
- viewport state is not an analysis input and cannot trigger runtime recomputation;
- M9.2 is product orchestration only: it does not own lifecycle, mutate harmonic identity, mutate Source Raw PRZ, or write M4 evidence;
- FIVE_ZERO remains quarantined, Alternate Bat remains fail-closed, HSI and RSI BAMM acceleration trigger remain unsupported;
- ISSUE-0066 remains claims-only and does not block this phase;
- no routine user-computer dependency.

## Acceptance

See specs/m9-phase-2-automated-harmonic-analysis-runtime.md.
