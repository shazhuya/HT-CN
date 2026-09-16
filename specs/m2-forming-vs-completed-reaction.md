# M2.11 Forming Arrival vs Completed Reaction Separation

## Why this stage exists

The M2.6-M2.10 walk-forward pipeline studies a **forming** structure: after X/A/B/C becomes observable, does price later reach the projected PRZ before that frontier retires?

That is not the same research question as Volume Three Reaction vs. Reversal. Once D exists, the relevant question becomes: after the completed structure is actually observable, does price produce the expected Type-I reaction and what later evidence exists for a larger reversal?

HT-CN therefore forbids using forming PRZ-arrival success as proof of post-D reversal quality.

## The confirmation-clock problem

A completed D is a swing pivot. With a right-side-confirmed Pivot algorithm, D is only known several bars after the historical D bar.

Measuring a 38.2%/61.8% reaction from D while pretending the structure was already known at D creates look-ahead bias. Price may have already completed much of the reaction before the D pivot is confirmed.

M2.11 introduces a second clock:

- `d_index`: historical terminal pivot location;
- `confirmation_bar`: first bar at which that terminal pivot is confirmed;
- `confirmation_lag_bars`: confirmation bar minus D bar;
- reaction observation begins strictly **after `confirmation_bar`**.

Any T1 hit between D and confirmation is recorded as `late_completion_signal` and excluded from actionable reaction rates.

## Reaction targets

For completed XABCD, AB=CD and 5-0 structures, M2.11 uses the existing Volume-Three Type-I reaction objectives:

- T1 = 38.2% retracement of the A-D reaction span;
- T2 = 61.8% retracement of the A-D reaction span.

For Shark, the source-specific completion-to-5-0 transition remains separate:

- T1 = 50%;
- T2 = 61.8%.

The targets are fixed from the completed geometry. Later outcome cannot change identity, PRZ, Pivot selection or geometry score.

## Outcome classes

A completed reaction record is classified as one of:

- `immature`: fewer future bars than the configured horizon after confirmation;
- `late_completion_signal`: T1 was already reached after D but before confirmation;
- `t2_within_horizon`: actionable confirmation, then T2 reached within the horizon;
- `t1_only_within_horizon`: actionable confirmation, T1 reached but T2 did not;
- `no_t1_within_horizon`: actionable confirmation, T1 not reached.

Only the final three classes enter actionable T1/T2 reaction rates.

## Historical extraction without replaying every bar

The full-history scan is safe for this purpose because HT-CN pivots are immutable right-side-confirmed events. Historical completed windows are reconstructed from those confirmed pivots, then each record is timestamped at its terminal Pivot `confirmed_at` bar.

The outcome clock never starts at D unless `confirmed_at == D`.

This avoids an O(N²) prefix replay while preserving the same first-observable timestamp that a bar-by-bar replay would have used.

## Separation from forming calibration

M2.11 preserves two distinct evidence namespaces:

| Stage | Question | Main outcome |
| --- | --- | --- |
| Forming | Does the XABC/other frontier reach its projected PRZ before retirement? | PRZ touch / frontier retirement |
| Completed | After the terminal pivot is confirmed, does the completed pattern react? | Type-I T1/T2 after confirmation |

Neither target is allowed to stand in for the other.

A future stage may calibrate structural-quality evidence against completed reaction outcomes, but it must use a separately purged chronological split and must freeze exact clauses before opening any completed-reaction Holdout.

## Current non-goals

M2.11 does **not**:

- claim that T1/T2 reaction implies a durable reversal;
- optimize Type-II rules;
- merge Shark with standard XABCD semantics;
- convert geometry score into probability;
- freeze a production quality policy;
- open the existing forming Holdout.

The immediate purpose is to establish a no-lookahead completed-reaction dataset so the next calibration stage asks the correct Volume-Three question.
