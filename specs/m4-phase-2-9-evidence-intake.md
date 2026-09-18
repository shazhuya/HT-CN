# M4 Phase 2.9 — Evidence Bundle Intake Revalidation

## Purpose

A transport-valid ZIP is not automatically research-evidence-ready.

The M4 handoff bundle may contain:

- the frozen legacy T0 baseline;
- immutable committed capture transactions;
- evidence-health output;
- transition output;
- prospective-observation output.

Phase 2.9 freezes the assistant-side intake rule: authoritative evidence is revalidated and
derived state is recomputed from the frozen baseline + committed transactions instead of
trusting the derived reports in the ZIP.

## Intake order

1. Verify transport integrity.
2. Extract only validated authoritative members to an isolated temporary directory.
3. Re-run committed-capture validation.
4. Re-validate frozen legacy baseline identity and cutoff.
5. Reconstruct the authoritative capture timeline.
6. Recompute lifecycle transition facts.
7. Recompute prospective observation facts.
8. Compare included derived reports with the recomputed facts.
9. Compare bundle-level provenance with the committed chain.
10. Produce one structured ready / ready_with_warnings / not_ready result.

## Hard blockers

The intake auditor fails closed on, at minimum:

- invalid transport integrity;
- no post-baseline committed capture when a T1/Tn handoff is expected;
- unexpected frozen baseline cutoff;
- authoritative transaction tamper or schema/coverage/id mismatch;
- mixed methodology fingerprints inside the committed chain;
- bundle methodology differing from the committed chain;
- bundle committed-capture count drift;
- latest capture date or transaction-id drift;
- bundle code-head mismatch with the latest committed capture;
- dirty-worktree provenance on a bundle that claims current capture;
- evidence-health blockers;
- transition report drift from authoritative recomputation;
- prospective-observation report drift from authoritative recomputation;
- methodology provenance drift in included derived reports;
- first committed capture not strictly after the frozen baseline;
- a bundle claiming transport_bundle_ready while intake finds blockers.

## Warnings

Derived reports are convenience products, not authoritative evidence.

If a derived transition or observation report is missing, the intake auditor may recompute it
from authoritative evidence and continue with an explicit warning.

A bundle marked `evidence_health_blocked` may be transport-valid for diagnosis, but the intake
result is always `not_ready`.

## T0 boundary

The current frozen T0 cutoff is:

`2026-09-17`

The generic intake engine accepts an explicit expected cutoff. The current M4 CLI defaults to
the frozen T0 date so an accidental baseline rewrite is detected immediately.

## Output boundary

The intake summary may report factual counts such as:

- committed capture dates;
- candidate counts;
- transition counts;
- lifecycle-state counts;
- prospective_new candidate counts;
- prospective_outcome_eligible candidate counts;
- confirmed full-day suspension counts.

It does not compute:

- returns;
- MFE / MAE;
- win rate;
- alpha;
- expected return;
- buy / sell ranking.

Those remain outside Phase 2 and require a separately frozen future outcome protocol.

## Methodology boundary

The intake auditor is an evidence-consumption and verification layer.

It does not change:

- harmonic identity;
- Fibonacci ratios;
- Source Raw PRZ;
- Source Terminal semantics;
- Source lifecycle;
- BAMM;
- Shark / 5-0 source rules;
- prospective enrollment rules.

Therefore the intake implementation is intentionally outside the methodology fingerprint.
