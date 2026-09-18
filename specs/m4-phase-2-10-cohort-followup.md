# M4 Phase 2.10 — Outcome Cohort Follow-up and Methodology v2

## Purpose

A candidate can leave the harmonic scanner while its underlying security continues trading.

Once a candidate has been prospectively enrolled into the future outcome cohort, stopping
market observation at scanner disappearance would create informative censoring: only
candidates that continue to satisfy scanner visibility would keep a price path.

Phase 2.10 separates two facts:

- **harmonic scanner presence / lifecycle**;
- **post-enrollment market observation**.

## Schema v3

Committed capture schema v3 contains two distinct row families:

### 1. journal_rows

Scanner-present harmonic candidates.

These rows may contain canonical Source lifecycle, action state, Source PRZ and current
harmonic evidence.

### 2. cohort_followup_rows

Previously outcome-enrolled candidates that are not returned by the current scanner.

They are always:

- `scanner_presence = absent`;
- evidence-only;
- not trade instructions;
- not alpha inference;
- without a new harmonic lifecycle or action state.

## Complete coverage rule

For every schema-v3 capture:

`followup_keys == prior_outcome_enrolled_keys - current_scanner_present_keys`

Missing or extra follow-up rows are hard blockers.

A follow-up may not be created for a candidate that was never previously outcome-enrolled.

## Traded follow-up

A normal traded-session follow-up requires:

- current capture-date market bar;
- `underlying_last_trade_date == capture date`;
- OHLC + volume present;
- `execution_context_gate = followup_observation_only`.

This is a market observation only. It does not imply the harmonic candidate remains active.

## Full-day suspension follow-up

A suspended follow-up requires positive full-day suspension evidence.

It carries:

- prior underlying last-trade date;
- no synthetic current-day OHLC/volume;
- `execution_context_gate = blocked_suspended`;
- daily-event provenance.

## Observation panel

The prospective observation report now consumes committed follow-up rows.

For an enrolled candidate that is scanner-absent:

- scanner presence remains `absent`;
- lifecycle/action remain null;
- market facts come from the follow-up row when available;
- market-observation counts include that real follow-up observation.

Thus scanner disappearance no longer deletes the underlying market path.

## Intake

Phase 2.9 intake recomputation consumes the same authoritative follow-up rows.

Included transition and observation reports are compared against fully recomputed:

- normalized rows;
- transition rows;
- observation rows;
- summaries and counts.

Derived reports remain non-authoritative caches.

## Methodology contract v2

Before the first post-T0 committed capture, the methodology identity contract is upgraded
from v1 to v2.

Fingerprint coverage expands from 32 to 37 files by adding:

- `src/htcn/research/capture_transaction.py`
- `src/htcn/research/cohort_followup.py`
- `src/htcn/research/lifecycle_transitions.py`
- `src/htcn/research/prospective_observations.py`
- `src/htcn/research/snapshot_manifest.py`

These files can change cohort chronology, enrollment normalization, censoring/follow-up
semantics, or the future observation panel and therefore must be frozen with the same
prospective methodology identity.

No post-T0 fingerprinted committed capture existed before this upgrade, so no prospective
future evidence is migrated or rewritten.

The T0 cutoff remains `2026-09-17`.

## Interpretation boundary

Phase 2.10 still does not define or compute:

- returns;
- MFE / MAE;
- win rate;
- alpha;
- expected return;
- buy/sell ranking.

It only ensures that a future preregistered outcome protocol will have an uncensored,
auditable market path for already enrolled candidates.
