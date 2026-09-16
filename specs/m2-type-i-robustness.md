# M2.19 — Type-I Early-Path Robustness

## Goal

M2.18 showed that some source-backed 3–5 bar price-path descriptions were associated with higher later T2 progression in visible data. M2.19 does not search for new conditions. It stress-tests **all six M2.18 predeclared cohorts** so Validation results cannot be used to cherry-pick only the strongest-looking path.

## Frozen target

The landmark is T+5 after the M2.17 Terminal Price Bar.

For every Train/Validation case whose T2 was still pending at T+5, the outcome is whether T2 is first reached from T+6 through the frozen 20-bar reaction horizon.

This prevents circular labels such as using "T2 already reached by T+3" to predict that same T2 event.

## Cohorts under test

No new thresholds are fitted. M2.19 reuses exactly the six M2.18 path descriptions:

- full PRZ exit by T+3;
- full PRZ exit by T+5;
- no PRZ overlap through T+3;
- no PRZ overlap through T+5;
- exit by T+3 + no overlap through T+3;
- exit by T+5 + no overlap through T+5.

These remain research proxies for Carney's qualitative 3–5 bar continuation language. They are not new harmonic identities or authoritative Carney confirmation rules.

## Robustness gates

A cohort is only labeled `robust_research_candidate=true` if all of the following survive in visible data:

1. positive later-T2 lift in both Train and Validation;
2. at least 60 gated pending Train cases and 20 gated pending Validation cases;
3. no single symbol above 25% of gated pending observations in either split;
4. positive lift after removing every symbol one at a time in both visible splits;
5. at least two jointly eligible pattern families, each with positive Train and Validation lift;
6. both bullish and bearish groups jointly eligible and positive in Train and Validation;
7. temporal stability: at least two of three eligible Train thirds positive and all eligible Validation halves positive;
8. at least two source scales in Train and Validation, with no scale above 80% share.

These are research-quality requirements, not trading rules.

## Holdout discipline

M2.19 reuses the exact M2.17/M2.18 chronological boundaries and forward-window purge. Cohort predicates and outcome summaries are evaluated only on Train and Validation. Holdout contributes only its sealed record count; its outcomes are never summarized, ranked or used to change the candidate library.

## Interpretation

Even a cohort that passes every robustness check remains:

- `eligible_for_policy_freeze=false`;
- descriptive historical evidence rather than a future probability;
- unable to alter Carney geometry, Pivot selection, PRZ, Terminal Price Bar or target construction;
- insufficient by itself to establish a validated Type-II reversal or an executable A-share trading policy.

The purpose of M2.19 is to distinguish repeatable early path behavior from sample concentration, family bias, direction bias, time-period luck and scale artifacts before any Holdout is opened.
