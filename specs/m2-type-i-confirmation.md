# M2.18 — Type-I Early-Path Evidence

## Purpose

M2.17 moved the execution clock to Scott M. Carney's source-aligned Terminal Price Bar: the bar that tests the final/extreme measurement of the projected PRZ. M2.18 studies the first five price bars after that event without changing harmonic identity and without pretending that a descriptive price-action proxy is a new Carney rule.

## Source boundary

Volume 3 describes the Type-I completion as the first test of the PRZ. After the reversal extreme is established, counter-trend behavior should become visible around T-Bar+2/T-Bar+3, without a PRZ retest, and clear continuation should be demonstrated within roughly three to five price bars.

The source language is qualitative. HT-CN therefore does **not** create an arbitrary numeric "Type-I confirmation score" or claim that one specific candle rule is authoritative.

## Fixed descriptive cohorts

M2.18 predeclares six path descriptions before looking at outcomes:

- full PRZ exit by T+3;
- full PRZ exit by T+5;
- no PRZ overlap through T+3;
- no PRZ overlap through T+5;
- full exit by T+3 plus no overlap through T+3;
- full exit by T+5 plus no overlap through T+5.

"Full PRZ exit" is intentionally conservative: for bullish structures, the entire bar must trade above the PRZ; for bearish structures, the entire bar must trade below it. It is a research proxy for demonstrative continuation, not a claim that Carney specified this exact machine rule.

## T+5 landmark design

A direct statement such as "T1 reached early predicts T1" would be tautological. M2.18 therefore separates early reaction from later progression.

At T+5 it reports:

- how often T1/T2 had already been reached by T+5;
- among cases where a target was still pending at T+5, how often the **first** hit occurred from T+6 through the frozen reaction horizon.

The second statistic is a landmark progression measure. It is not profitability, win probability, trade advice or proof of a larger reversal.

## Split and leakage control

M2.18 reuses the exact M2.17 chronological boundaries. Forward labels crossing Train→Validation or Validation→Holdout are purged using the existing observation-end date.

No thresholds are learned from Validation. No cohort is selected by Holdout performance. Holdout outcome fields remain sealed and are never summarized by M2.18.

## Interpretation limits

The report is evidence only:

- `policy_frozen = false`;
- every cohort has `eligible_for_policy_freeze = false`;
- pattern identity and geometry score remain untouched;
- early-path behavior cannot be renamed as a validated Type-II reversal;
- a target touch is a historical price reaction, not a trading return.

The next stage may use this evidence to decide which source-backed confirmation dimensions deserve deeper robustness tests, but only after family/symbol/time concentration is examined and without opening the sealed Holdout.
