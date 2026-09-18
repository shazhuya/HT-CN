# M4 Phase 3.0 — Preregistered Outcome Protocol v1

## Status

`m4-outcome-v1` is frozen before the first real post-T0 prospective outcome is observed.

This protocol does not change the M4 capture methodology. The capture/evidence contract remains:

- transaction schema v5;
- prospective observation schema v4;
- methodology contract v4;
- exact capture-methodology freeze `c774c54928c33361952bf1a612a8555633449625`.

The machine-readable authority for this outcome protocol is:

`research/m4-outcome-protocol-v1.json`

## Why this is separate from capture methodology

Capture answers:

- who entered the cohort;
- what was observable at enrollment;
- what price basis and Source-clock seed were frozen.

Outcome evaluation answers:

- what happened after enrollment.

The two contracts must not be silently coupled. A future change to outcome windows or metric
definitions must create a new outcome protocol version without rewriting already captured
candidate evidence.

## Cohort

Only rows that were prospectively admitted by the frozen capture methodology may enter:

`prospective_outcome_eligible = true`

Excluded:

- T0 baseline inventory;
- baseline-existing candidates;
- source-fidelity-blocked patterns;
- candidates already terminal at enrollment;
- candidates lacking formal QFQ provenance;
- candidates lacking frozen Source-clock seed.

## Outcome market path

The outcome path is **not** the sequence of dates on which the user happened to run M4 capture.

That would make outcome results depend on capture cadence.

The v1 outcome path uses the full local M1 logical daily history:

`base daily + daily_delta overlay`

for the already-frozen instrument/candidate.

This is outcome follow-up data only. It may not create or backdate:

- candidate identity;
- enrollment;
- Source Raw PRZ;
- the frozen signal seed.

### Trading-bar clock

All fixed windows use real traded bars.

Confirmed full-day suspension:

- remains a real calendar observation;
- does not count as a traded bar.

Thus T+5 means five traded bars after the Source Terminal Price Bar, not five calendar days and
not five M4 capture snapshots.

## Price-basis rule

The M1 outcome path must remain on the enrollment price basis.

If current path basis differs from the enrollment `price_basis_id`:

- pre-drift mature facts remain evidence;
- any price comparison requiring post-drift data is unresolved;
- v1 does not automatically rebase.

A future rebasing method requires a separately preregistered protocol.

## Source reconstruction

The evaluator must reuse, not duplicate:

- `htcn.harmonic.execution.observe_source_execution`;
- `htcn.harmonic.source_lifecycle.derive_source_lifecycle`.

Inputs are the frozen enrollment seed plus the full outcome market path.

If reconstruction says Source Terminal occurred before the frozen enrollment date, this is an
evidence contradiction, not a successful historical reconstruction.

## Primary Source-event outcomes

### Source Terminal

Record:

- observed / not yet observed;
- terminal trade date;
- terminal price.

### Type-I

Volume III establishes the first PRZ test / Terminal Price Bar as the execution clock and expects
clear continuation within approximately 3–5 bars. HT-CN's already frozen canonical lifecycle
uses the 38.2% reaction target within five traded bars as the strict Type-I confirmation
operationalization.

v1 records:

- 38.2% hit in T+1..T+5;
- first 38.2% hit offset;
- first 61.8% hit offset;
- later 38.2% as reaction-only when outside the strict five-bar window.

The 38.2% and 61.8% levels come from the existing Source execution audit. The outcome evaluator
must not recalculate them using a different formula.

### Type-II price structure

Record the existing strict production price path:

- first reversal-direction Source PRZ exit;
- secondary re-entry;
- terminal-side retest;
- reversal-direction exit after the Type-II terminal retest.

This is **price-structure evidence**.

Volume III also requires indicator confirmation for a full Type-II reversal assessment. Until a
separate indicator-confirmation outcome protocol is frozen, v1 must not rename price-only
`reversal_evidence` as complete Carney Type-II proof.

### Shark boundary

The canonical lifecycle may use generic 38.2%/61.8% reaction classification for Shark.

Those are not Shark-specific trade-management targets.

The Volume III Shark first management objective — the earlier/lesser relevant 50% versus
Reciprocal AB=CD measurement — is outside outcome-v1 because the current enrollment evidence
does not freeze the complete dedicated management-target input set.

Adding that outcome later requires a new preregistered protocol.

## Descriptive market-path metrics

Metrics begin at T+1. The Terminal bar itself is excluded from post-terminal excursion windows.

Frozen windows:

- 5 traded bars — primary, Source-aligned;
- 10 traded bars — secondary HT-CN descriptive window;
- 20 traded bars — secondary HT-CN descriptive window.

For bullish candidates:

- MFE = maximum post-terminal high minus terminal price;
- MAE = terminal price minus minimum post-terminal low.

For bearish candidates the signs are mirrored.

Each window records:

- raw MFE / MAE price distance;
- MFE / MAE as percentage of terminal price;
- MFE / MAE in reaction-span units.

Reaction span:

`abs(reaction_anchor_price - terminal_price)`

This denominator is harmonically meaningful because 38.2% and 61.8% reaction targets are measured
from that same span.

A fixed N-bar window is mature only after all N traded bars are available on an uninterrupted
compatible price basis. An incomplete window is marked immature rather than treated as a shorter
complete window.

## Right censoring

No arbitrary "failed after 30/60 days" rule is introduced.

- Terminal not yet observed -> right-censored / ongoing.
- Type-II not yet observed -> right-censored / ongoing.
- Missing required market data -> unresolved.
- Price-basis interruption -> unresolved after the interruption.

This prevents unresolved candidates from being mechanically converted into failures.

## No trading P&L in v1

Outcome-v1 intentionally does not define:

- executable entry;
- stop loss;
- position size;
- commission/tax/slippage;
- T+1 trading P&L.

Therefore it does not calculate trade return.

Execution-performance research must be a separate protocol because A-share execution constraints
are not the same thing as Carney Source-event validity.

## No win rate / alpha in v1

v1 does not create a binary win/loss label.

It therefore does not publish:

- win rate;
- alpha;
- benchmark excess return;
- p-values;
- significance tests;
- strategy rankings.

It first answers the more fundamental prospective question:

**what Source events and post-terminal market paths actually occurred under one frozen
methodology?**

## Data revision audit

Every generated candidate outcome must include:

- candidate key;
- enrollment methodology fingerprint;
- outcome protocol ID;
- outcome as-of trade date;
- price basis ID;
- ordered traded-date path used;
- canonical SHA-256 of the outcome OHLCV path.

If the same candidate and same outcome-as-of date later produce a different canonical path hash,
the evaluator reports data drift instead of silently replacing the previous result.

## Source / engineering separation

Carney source-aligned elements:

- first PRZ test;
- Terminal Price Bar;
- immediate 3–5 bar Type-I confirmation concept;
- 38.2% / 61.8% automatic reaction objectives;
- Type-II secondary PRZ test;
- requirement for price + indicator confirmation for full Type-II reversal interpretation.

HT-CN engineering elements:

- full M1 logical-history outcome source;
- QFQ basis identity;
- canonical path hash;
- 10/20-bar secondary descriptive windows;
- machine-readable censoring states.

Those engineering choices are explicitly not attributed to Carney.
