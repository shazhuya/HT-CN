# M2.17 — Source-Aligned Terminal Price Bar Clock

## Why this stage exists

M2.11 deliberately measured completed-pattern reactions only after the terminal historical
Pivot became right-confirmed. That is a valid **confirmation-latency audit**, but M2.14/M2.16
show that many reactions have already occurred by then. The 45-symbol sample also proves that
`confirmation_lag_bars` is mechanically identical to the fixed Pivot `source_scale`, so
"fast confirmation" is scale context rather than an independent harmonic-quality factor.

Scott M. Carney Volume 3 defines a different execution clock:

- the **Terminal Price Bar (T-Bar)** is the bar that tests the final/extreme measurement of the
  Potential Reversal Zone;
- that T-Bar marks the point where the pattern is considered officially complete for execution
  purposes;
- execution/confirmation assessment begins immediately thereafter (T-Bar+1);
- Type-I behavior is expected to demonstrate clear continuation within roughly 3–5 price bars;
- 38.2% and 61.8% are the standard automatic Type-I reaction objectives discussed in Volume 3.

Therefore HT-CN must not equate "official completion for execution" with "right-confirmed D
Pivot". These are two separate clocks.

## Two-clock model

### 1. Terminal Price Bar clock — source-aligned execution research

A no-lookahead forming projection already supplies a PRZ before the future terminal point is
known. M2.17 watches that frozen projection forward. For a bullish structure the official
Terminal Price Bar is the first still-active future bar whose low tests the PRZ low/extreme.
For a bearish structure it is the first still-active future bar whose high tests the PRZ
high/extreme.

Merely overlapping any part of the PRZ is recorded as `first_prz_entry_bar`; it is **not**
automatically promoted to the official T-Bar. This preserves Carney's distinction between
entering a zone and testing its final/extreme measured level.

If the PRZ had already been touched before the forming signal became observable, the projection
remains late and is ineligible for this execution clock.

### 2. Confirmed-Pivot clock — retrospective structural audit

M2.11–M2.16 remain valuable. They answer a different question: after the terminal extreme is
later confirmed as a Swing/Pivot, does the completed structure still produce a reaction?
That clock is intentionally conservative and useful for structural validation, but it is not
used as a substitute for Carney's T-Bar execution timing.

M2.17 records whether the source-aligned T-Bar later becomes the exact terminal bar of an
engine-confirmed completed pattern. This creates an explicit bridge between execution-time
projection and retrospective identity confirmation.

## Type-I reaction audit

After a T-Bar is observed, M2.17 measures:

- T1/T2 from the T-Bar extreme;
- first full exit from the PRZ in the reversal direction;
- whether price overlaps the PRZ during T+1..T+3 and T+1..T+5;
- whether the same T-Bar is later confirmed by the harmonic engine;
- bars from T-Bar to later Pivot confirmation.

For standard projected structures the current HT-CN Type-I convention uses the Volume-3
38.2%/61.8% reaction objectives measured from the terminal extreme toward A. Shark retains its
50%/61.8% B-to-terminal reaction convention already used elsewhere in M2.

The source says continuation should be clear within 3–5 bars, but "clear" is qualitative.
HT-CN therefore records objective 3/5-bar evidence and **does not invent a numeric Carney
pass/fail threshold**.

## Anti-leakage and retirement

The projection must exist before the T-Bar. The forward search starts strictly after the
forming signal bar and stops at the earlier of:

- the configured forming observation horizon;
- the frontier-retirement bar;
- the end of available history.

A retired projection cannot claim a later T-Bar. Future outcome data cannot alter the original
forming signal, prefix pivots, PRZ, identity label, or retirement time.

## Independent calibration split

Terminal-Bar reaction outcomes get their own chronological 60/20/20 Train/Validation/Holdout
split and their own forward-window purge based on T-Bar + reaction horizon. The forming split
and confirmed-Pivot completed-reaction split are not reused because they represent different
signal clocks.

The default 60/30/10/10 sample floor remains an HT-CN research-governance choice, not a Carney
rule or a statistical guarantee. Holdout outcome rates remain sealed.

## Interpretation boundary

A T-Bar event means a previously observable, source-valid projection reached its official PRZ
completion extreme. It does **not** mean a profitable trade, a validated larger reversal, or a
production trading instruction. Type-I reaction evidence and later confirmed identity are
reported separately.
