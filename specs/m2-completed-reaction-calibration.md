# M2.12 — Completed-Reaction Purged Calibration

## Purpose

M2.12 separates a **completed harmonic structure** from the later price reaction that can
actually be observed after the terminal Pivot has been confirmed.

This layer is research-only. It must not modify Scott M. Carney geometry, pattern identity,
PRZ construction, Pivot selection, tolerance rules or `geometry_score`.

## Signal clock

The historical D/C completion bar is not automatically observable in real time. HT-CN uses
the terminal Pivot's `confirmed_at` bar as the first completed-structure signal timestamp.

Therefore:

- price movement between the historical completion pivot and `confirmed_at` is
  **pre-confirmation** evidence;
- if T1 has already been reached before confirmation, the case is
  `late_completion_signal`;
- late cases are excluded from actionable post-confirmation reaction calibration.

## Independent reaction target

Completed-reaction calibration is not the same target as forming-pattern PRZ arrival.

- XABCD / standalone AB=CD / 5-0: post-confirmation Type-I 38.2% and 61.8% reaction
  objectives;
- Shark: its source-specific 50% and 61.8% reaction objectives.

The two research targets must never share a success label.

## Purged chronological split

Actionable mature completed reactions are split chronologically using the same
train/validation/holdout discipline as other HT-CN research, but with their own timestamps:

- `signal_trade_date`: terminal Pivot confirmation date;
- `observation_end_trade_date`: exactly `reaction_horizon` trading bars after signal, capped
  at the available data end for immature rows;
- any train/validation label window crossing the next split boundary is purged.

Holdout outcomes are not summarized. The emitted reaction artifact redacts raw outcomes for
records at or after the Holdout boundary.

## Sample floor

The first real 13-symbol pilot produced only 18 mature actionable completed reactions.
That is too small for a useful completed-reaction quality fit.

M2.12 therefore uses the following **HT-CN governance floor**, not a Carney rule and not a
claim of statistical sufficiency:

- actionable total: 60
- post-purge train: 30
- post-purge validation: 10
- post-purge holdout: 10

Below this floor the status must remain:

`completed_reaction_sample_insufficient_holdout_sealed`

No quality threshold may be promoted from that state.

## Acceptance

M2.12 passes its engineering gate when:

1. signal timing starts at Pivot confirmation rather than historical completion;
2. late and immature cases cannot enter actionable calibration;
3. exact trading-bar observation-end timestamps are emitted;
4. chronological boundary purge is deterministic;
5. Holdout summaries expose counts/identity metadata only;
6. raw Holdout outcomes are redacted from the emitted completed-reaction artifact;
7. insufficient sample is reported as a research finding, not disguised as calibration
   success;
8. provider coverage failure is allowed to fail the autonomous CI job rather than being
   hidden by `continue-on-error`.
