# M4 Phase 2.11 — Price-Basis Provenance and Methodology v3

## Purpose

HT-CN harmonic analysis operates on a continuous A-share price series.

For formal analysis the preferred basis is local QFQ. If QFQ factors are unavailable or
historically incomplete, the service may fall back to raw prices for display, but that raw
fallback is not a formal harmonic conclusion.

Before the first post-T0 future capture, M4 therefore freezes the price coordinate system as
part of prospective evidence provenance.

## Formal price basis

Formal prospective evidence accepts only:

- `qfq`;
- `qfq_carry_forward`.

A raw fallback:

- may remain visible for diagnosis;
- is `eligible_for_validation=false`;
- cannot enter the strict prospective outcome cohort;
- cannot participate in an authoritative full-universe M4 capture.

Any initialized instrument lacking formal QFQ basis causes the authoritative capture to fail
closed rather than produce a partial mixed-basis snapshot.

## Deterministic QFQ basis identity

Each formal analysis exposes:

- `price_mode`;
- `price_basis_id`.

The QFQ basis ID is SHA-256 over the ordered sequence of QFQ **factor change points**.

Consequences:

- appending later dates with the same carried-forward factor does not change the basis ID;
- a new factor regime changes the basis ID;
- a revision to historical factor regimes changes the basis ID.

The identity is provenance for the price coordinate system, not an investment signal.

## Authoritative schema v4

Committed capture schema v4 requires valid QFQ price provenance on every:

- scanner-present journal row;
- scanner-absent cohort follow-up row.

The price fields participate in deterministic transaction identity because they are part of
the row payload.

Old transaction schemas remain readable for audit, but a v1-v3 chain cannot silently accept
a v4 append.

## Prospective enrollment

D-024 is tightened:

A prospective-new candidate cannot enter the future outcome cohort unless:

- it already satisfies the existing forming/pre-terminal/Source-PRZ rules;
- the observation is a traded session;
- `eligible_for_validation=true`;
- the price mode is formal QFQ;
- `price_basis_id` is present.

This does not alter harmonic identity. It defines which observations are admissible for
prospective outcome research.

## Follow-up

D-032 remains active.

If an enrolled candidate becomes scanner-absent, market follow-up continues and now also
records the current price basis.

A follow-up remains scanner-absent and lifecycle-less; price-basis provenance does not
reanimate the harmonic candidate.

## Prospective observation schema v3

The observation panel freezes the enrollment basis and reports for each later observation:

- current price mode;
- current price basis ID;
- whether current basis equals enrollment basis.

Candidate summaries expose:

- enrollment price mode;
- enrollment price basis ID;
- price-basis drift snapshot count;
- first drift date;
- whether the basis stayed stable across observed snapshots.

## Basis drift rule

A basis change is not automatically rebased.

Phase 2 only records the drift.

It does not:

- rewrite frozen Source PRZ;
- rewrite historical candidate identity;
- backdate a new basis;
- calculate cross-basis returns;
- calculate cross-basis MFE/MAE;
- infer profit/loss.

Intake surfaces basis drift as:

`price_basis_drift_present_future_outcome_rebase_required`

This is a warning for future outcome analysis, not a current evidence-integrity blocker.

A future outcome protocol must preregister an explicit rebasing method before any cross-basis
target-hit or return statistic is computed.

## Methodology v3

Because admissible prospective observations and future outcome comparability change, the
methodology contract advances from v2 to v3.

Component count remains 37.

Exact methodology-v3 freeze commit:

`2b0aa92d292410098d9678a3bfd3102f3df1ed4b`

The first post-T0 future committed capture had not yet been created when v3 was frozen, so
no future evidence was migrated, rewritten or mixed across methodology versions.

D-033 remains historical evidence of the prior v2 freeze but is superseded for the first
actual T1 by D-034.

## Source boundary

This Phase does not claim that Carney specifies QFQ, A-share adjustment factors or this basis
fingerprint.

Those are HT-CN A-share data/evidence engineering rules.

Carney source rules for pattern identity, PRZ, Terminal Price Bar, Type-I/Type-II and BAMM
remain unchanged.

## Outcome boundary

No return, MFE, MAE, win rate, alpha, expected return or buy/sell ranking is introduced by
Phase 2.11.


## Current supersession — Phase 2.12

Phase 2.11 froze price-coordinate provenance under transaction schema v4 / methodology v3.

Before the first real T1 capture, the outcome-sufficiency audit found that an enrolled candidate
could disappear from the scanner before Source Terminal and leave future OHLC without the
original forming signal/reaction-anchor inputs needed by the existing Source execution observer.

Phase 2.12 therefore advances the current T1 protocol to:

- committed capture schema v5;
- prospective observation schema v4;
- methodology contract v4;
- 37 methodology component paths;
- exact methodology freeze commit `c774c54928c33361952bf1a612a8555633449625`.

All D-034 price-basis rules remain active. Phase 2.12 adds frozen Source-clock reconstruction
seed; it does not remove or weaken price-basis provenance.
