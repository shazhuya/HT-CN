# M2.21 — One-Time Type-I Holdout Pre-registration

## Purpose

M2.20 resolves the nested T+3/T+5 early-exit evidence using only Train and Validation. M2.21 freezes the single confirmatory question **before** any M2.17 Holdout outcome is opened.

This stage does not evaluate Holdout.

## Eligible hypothesis

The pre-registration is created only when M2.20 returns exactly one visible-data hypothesis and marks it eligible for pre-registration.

Two possible contrasts are supported:

- if M2.20 selects `full_prz_exit_by_t3`, the confirmatory contrast is `exit_by_t3` versus `exit_on_t4_t5`; this tests whether earlier exit adds information beyond merely exiting by T+5;
- if M2.20 selects `full_prz_exit_by_t5`, the confirmatory contrast is any full PRZ exit by T+5 versus no full PRZ exit by T+5.

No alternate contrast may be substituted after Holdout is opened.

## Frozen population and endpoint

Population:

- M2.17 source-aligned Terminal Price Bar event;
- event is mature for the frozen 20-bar reaction horizon;
- T2 is still pending at T+5;
- record belongs to the already-sealed M2.17 Holdout.

Primary endpoint:

> first T2 hit from T+6 through T+20.

## Confirmatory method

The primary effect is the absolute difference in endpoint proportions between the exposure and comparator groups.

The one-time Holdout test will use a 95% Newcombe score confidence interval for the difference of two independent proportions.

A hypothesis is confirmed only when:

- each Holdout group contains at least 20 eligible records; and
- the lower bound of the 95% Newcombe interval for exposure-minus-comparator is strictly greater than zero.

If either group contains fewer than 20 records, the result is `inconclusive`, not success and not failure.

If the confidence-interval lower bound is not above zero, the result is `not_confirmed`.

## Multiplicity and secondary diagnostics

There is exactly one primary confirmatory test.

Direction, pattern family, source scale and instrument diagnostics may be reported after Holdout is opened, but they are descriptive only. They cannot rescue or overturn the primary result and cannot create a new post-hoc rule.

## Holdout state

M2.21 must emit:

- `holdout.sealed = true`;
- `holdout.outcomes_exposed = false`;
- `holdout_open_authorized = false`.

Opening the Holdout requires a later, separate committed stage so that the hypothesis, endpoint, contrast and success criterion exist in repository history before the irreversible evaluation.
