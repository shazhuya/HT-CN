# M2.20 — Type-I Exit Timing: Nested-Cohort Resolution

## Problem

M2.19 found two robust visible-split cohorts:

- full PRZ exit by T+3;
- full PRZ exit by T+5.

These are not independent factors. Every T+3 exit is also a T+5 exit. Counting both as separate evidence would double-count the same early path behavior and make the research look stronger than it is.

## Frozen target

The outcome remains unchanged from M2.18/M2.19:

> among Terminal-Bar cases whose T2 is still pending at T+5, did the **first** T2 hit occur from T+6 through the frozen 20-bar reaction horizon?

No new target is introduced.

## Mutually exclusive early-path groups

M2.20 partitions the visible Train/Validation population into exactly three non-overlapping groups:

1. `exit_by_t3` — the entire bar has moved beyond the PRZ in the reversal direction by T+3;
2. `exit_on_t4_t5` — no full exit by T+3, but the first full exit occurs on T+4 or T+5;
3. `no_full_exit_by_t5` — no full PRZ exit by T+5.

Only T+1..T+5 information is used for group membership.

## Predeclared decision rule

M2.20 does not search arbitrary timing thresholds. It resolves only the already-existing nested T+3/T+5 candidates using this fixed rule:

- choose `full_prz_exit_by_t3` only if `exit_by_t3` has a higher later-T2 rate than `exit_on_t4_t5` in **both** Train and Validation, and pooled <=T+5 exit still beats no-exit in both;
- otherwise choose `full_prz_exit_by_t5` only if `exit_on_t4_t5` itself beats `no_full_exit_by_t5` in both Train and Validation, and pooled <=T+5 exit beats no-exit in both;
- otherwise select no hypothesis.

This rule distinguishes a true speed gradient from a simpler five-bar deadline.

## Sample floor

The exclusive `exit_by_t3` and `exit_on_t4_t5` groups must each contain at least:

- 60 Train pending-T2 cases;
- 20 Validation pending-T2 cases.

These floors are declared before Holdout is opened.

## Leakage control

M2.20 reuses the M2.17 chronological split and purge boundaries.

- Holdout rows are assigned only to preserve the count.
- Holdout outcomes are never summarized.
- No numeric threshold is fit from outcomes.
- Carney geometry, PRZ construction, Pivot selection, Terminal Price Bar and target definitions are unchanged.

## Output semantics

`selected_hypothesis` means only that one visible-data hypothesis is sufficiently isolated to be **pre-registered for a later one-time Holdout test**.

It does **not** mean:

- production policy is frozen;
- the rule is profitable;
- the rule predicts future returns;
- Holdout has passed.

`eligible_for_policy_freeze` therefore remains `false` in M2.20.
