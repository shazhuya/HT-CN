# M3 Workbench — Phase 1

Date: 2026-09-16

## Goal

M3 turns the already-validated M2 harmonic core into a Chinese-first A-share research workbench. It does **not** rewrite Carney geometry and does not create automatic trading instructions.

The default screen should answer three questions before exposing deep audit detail:

1. **现在在哪** — the current harmonic lifecycle state;
2. **先看哪** — the first observable checkpoint that can advance or invalidate the current interpretation;
3. **到了再看哪** — the next lifecycle checkpoint after the first one is reached.

## Phase-1 lifecycle mapping

The UI consumes existing M2 fields only. It does not create a new pattern identity.

### Forming

- current: forming / not completed;
- first checkpoint: actual PRZ test and auditable Terminal Price Bar;
- next checkpoint: departure from PRZ and transition into Type-I observation.

### Completed, no reaction audit yet

- current: geometry completed / reaction pending;
- first checkpoint: leave PRZ and progress toward T1 (38.2%);
- next checkpoint: T2 (61.8%) or secondary PRZ retest.

### Type-I T1 reached, T2 not reached

- current: Type-I reached T1;
- first checkpoint: T2 vs. secondary PRZ retest, whichever occurs first;
- next checkpoint: finish Type-I or switch to Type-II candidate audit after a retest.

### Type-I T2 reached

- current: Type-I reached T2;
- first checkpoint: secondary PRZ retest;
- next checkpoint: independent Type-II evidence after the retest.

### Secondary PRZ retest / Type-II

- current state is derived from the existing `type_ii_evidence_state` and retest fields;
- price evidence and Wilder RSI evidence remain separate from geometry identity;
- third PRZ test / failure remains a later audit state.

## Layering rule

M3 must keep these layers visibly separate:

- **Source geometry**: pattern identity, nodes, Fibonacci measurements, PRZ;
- **Lifecycle evidence**: Terminal Price Bar, Type-I targets, PRZ retest, Type-II evidence;
- **Historical statistical evidence**: frozen Holdout/external replication, never presented as current-symbol probability;
- **A-share execution context**: deferred to M5 and must not alter Carney identity/PRZ.

## UI rules

- Chinese-first labels;
- compact cards, readable on desktop and mobile;
- state summary appears next to/above the chart, before deep ratio audit;
- wording is observational, not `买入/卖出/加仓/减仓` instruction;
- latest close and PRZ boundary may be displayed as context;
- changing the selected candidate must immediately change the lifecycle navigator.

## Automated acceptance

Phase 1 is accepted when:

- TypeScript/Web build passes;
- deterministic Playwright fixture renders the lifecycle navigator;
- the fixture verifies the completed/reaction-pending state and no-trade-signal disclosure;
- existing harmonic chart, ratio audit and PRZ rendering remain present;
- GitHub CI passes on `m3/workbench`.

Later M3 phases will expand deterministic coverage for forming, T1, T2, retest and Type-II states and tighten visual regression without changing M2 source geometry.
