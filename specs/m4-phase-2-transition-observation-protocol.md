# M4 Phase 2 — Transition and Prospective Observation Protocol

## Purpose

Turn the append-only M4 journal into a capture-aware factual observation stream without defining profitability or alpha.

## Capture chronology

The lifecycle journal is candidate-level and cannot represent a full capture day with zero candidates.

The append-only snapshot manifest is therefore authoritative after activation.

Rules:

- one manifest row per captured as-of trade date;
- one code head per date;
- complete instrument coverage required;
- candidate_count must equal journal rows on that date;
- zero-candidate captures remain explicit;
- post-activation journal dates without manifest fail closed;
- pre-manifest T0 journal dates are retained as legacy baseline.

## Transition semantics

Transition engine consumes the explicit capture timeline and records only factual state changes:

- baseline_observed;
- new_candidate;
- persisted_same_state;
- lifecycle_changed;
- action_changed_only;
- scanner_disappeared;
- scanner_reappeared.

Scanner disappearance is not invalidation.

## Prospective observation

Only D-024 outcome-enrolled candidates enter the observation panel.

Each captured snapshot records:

- scanner presence;
- consecutive captured-snapshot absences;
- lifecycle/action state when present;
- execution/context state;
- next-key price/role;
- Source Terminal date;
- raw as-of OHLC/volume when present.

Milestones retain first observed dates for lifecycle states, Source Terminal, scanner absence and reappearance.

## Time semantics

`captured_snapshot_index` counts actual recorded snapshots after outcome enrollment.

It is deliberately not named trading-session index. Missing captures are not silently imputed.

## Outcome boundary

Phase 2 does not compute:

- returns;
- profit/loss;
- MFE/MAE;
- win rate;
- alpha;
- ranking;
- buy/sell scores.

Those require a separately frozen future protocol.
