# M2 Walk-Forward Forming Calibration

## Purpose

This stage evaluates whether an HT-CN *forming* harmonic projection had genuine forward value at the moment it first became knowable. It is intentionally different from the completed-pattern calibration dataset, which starts only after D/C completion is already known.

The output is research evidence only. It is not a win rate, a trading model, or a reason to mutate Carney identity rules.

## Information boundary

A projection may be emitted only when every frontier pivot used by that projection is already confirmed.

For a Pivot scale `S`, a center bar is not knowable as a pivot until `S` right-side bars have closed. HT-CN therefore stores each raw pivot event with `confirmed_at = center + S` and replays those events in confirmation order.

A critical anti-leakage rule follows:

> Never collapse the full historical pivot sequence first and then filter it by date.

A later, more-extreme pivot of the same kind can replace an earlier live pivot in the final collapsed history. If the final sequence were filtered after the fact, the earlier pivot would disappear from dates when it was genuinely known. The walk-forward engine instead collapses only events whose `confirmed_at` is at or before the current replay cutoff.

## Event-driven replay

The forming frontier can change only when a new pivot is confirmed. Replaying every daily bar would therefore repeat identical harmonic geometry many times and would be unnecessarily expensive.

HT-CN precomputes raw confirmation events, then advances only on their confirmation bars. Precomputation is a computational optimization: future events remain hidden until their own `confirmed_at` time.

At each event the engine evaluates only the current frontier for each schema:

- standard M/W: current `X-A-B-C` -> projected D / PRZ;
- standalone AB=CD: current `A-B-C` -> projected D / PRZ;
- Shark: current `0-X-A-B` -> projected C / PRZ;
- 5-0: current `X-A-B-C` -> projected D / PRZ.

Completed structures are matched later by the same pattern/schema/direction and exact prefix pivot indices.

## First-signal policy

The same physical frontier can appear on several Pivot scales. The research record uses the first time the frontier becomes available in real time. Later scale confirmation is not allowed to move the original signal timestamp backward or improve its original quality fields.

If several scales reveal the same frontier on the same bar, the record stores all of those `signal_scales`. Representative selection is based only on source tolerance and projected PRZ compactness, never on later outcome.

## Late-signal detection

Pivot confirmation itself creates latency. Price can begin moving toward the projected PRZ while the terminal frontier pivot is still waiting for right-side confirmation.

Therefore HT-CN explicitly checks the bars between the terminal pivot and the signal bar. If the projected PRZ was already touched during that interval, the projection is labelled:

`late_signal_prz_already_touched`

Such a record remains useful for studying confirmation lag, but it is excluded from forward-eligible checkpoint denominators.

## Frontier retirement

A forming projection is live only while at least one configured scale still retains the same physical frontier. Once a later confirmed pivot changes every scale away from that prefix, the old projection is marked retired.

A touch of the old PRZ *after* retirement is not credited as an active forecast success. This prevents stale historical projections from appearing successful merely because price eventually revisits the old level.

## Outcomes

For each first signal, HT-CN records independently:

- first future PRZ touch;
- whether the touch happened before frontier retirement;
- physical completion terminal bar, when a matching completed identity later appears;
- completion confirmation bar;
- frontier retirement bar;
- available future history;
- whether the signal was already late when emitted.

The default research horizon is 60 bars. The report also summarizes fixed 10/20/40/60-bar checkpoints. These horizons are HT-CN research parameters, not Carney identity rules.

Outcome classes are:

- `late_signal_prz_already_touched`
- `engine_completed_within_horizon`
- `prz_touched_within_horizon`
- `frontier_retired_before_touch`
- `immature`
- `no_prz_touch_within_horizon`

## Anti-leakage contract

Future outcomes must never change:

- pattern identity;
- projected PRZ;
- first-signal bar/date;
- source scale;
- source tolerance status;
- signal-time distance to PRZ;
- signal-time quality fields.

The walk-forward report is descriptive evidence for later calibration. Any future quality model must be trained and evaluated with explicit chronological train/validation/test separation rather than optimizing on the same history used for evaluation.
