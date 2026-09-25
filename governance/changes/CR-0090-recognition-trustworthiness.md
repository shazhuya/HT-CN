# CR-0090 — Recognition trustworthiness and detector correctness

status: validation_green
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 04aa35737f7d58c2ab12bca62ba536c3970ce9ef
target: main
milestone: M9.post_release
work_branch: m9/recognition-trustworthiness-v1

## Trigger

The production recognition work in CR-0089 proved hosted availability, practical candidate output,
Pine R3.4 behavioral reproducibility and 1D/60m/15m coverage, but those gates do not measure
detector correctness against independent ground truth. Candidate counts and green CI are not correctness evidence.

The user explicitly requires the project to stop expanding peripheral product features and focus on
the core question: can HT-CN recover the correct harmonic swing nodes from raw OHLC without future
leakage or uncontrolled false positives?

## Objective

Build a correctness program before production detector changes: fixed ground truth, one-to-one
matching, node error, failure-stage attribution, adversarial/synthetic-in-real corpora and streaming
invariance. Carney identity, Source Raw PRZ, M4 methodology and Outcome Engine stay frozen.

## Phase 0 gate

The first deliverable is intentionally diagnostic, not a new detector.

Phase 0 must produce a deterministic benchmark report from fixed generated fixtures and show:
- denominator and truth identities;
- TP / FP / FN;
- precision / recall / F1;
- exact-node and tolerant-node match;
- node MAE;
- authoritative failure-stage counts;
- benchmark corpus fingerprint.

No recognition tuning is allowed until this baseline exists and is reproducible in hosted CI.

## Scope

Allowed:
- recognition benchmark/oracle infrastructure;
- pivot/swing/candidate diagnostics;
- later experimental detector modules isolated from production;
- tests, scripts and minimal governance needed for the experiment.

Forbidden in this Change:
- UI expansion;
- win-rate/alpha/profitability claims;
- M4 capture methodology edits;
- Outcome Engine edits;
- Source Raw PRZ or CARNEY_RULES relaxation;
- Five-Zero or Alternate Bat production promotion;
- using the user's Windows computer as routine test infrastructure.

## Success meaning

A version is better only when fixed benchmark evidence improves detector correctness without
violating no-lookahead or materially collapsing precision. More candidates, more files, more tests
or more UI do not count as recognition improvement by themselves.


## Validated evidence

- Gate 0 — `A-20260925-0090-001`, run `36163533018`: legacy authoritative lost
  100/100 minor-swing cases at `candidate_window_missing`; bounded graph recovered 100/100 exact.
- Gate 1 — `A-20260925-0090-002`, run `36166500765`, artifact `10878190860`:
  skip=6 recovered 120/120 randomized primary structures exactly; 30 invalid-B/C/D negatives
  remained clean; forced future replacement erased final-history 24/24 while event-sourced
  streaming preserved 24/24 with zero confirmed-history mutation.
- Detailed corpus hashes, counts, limitations and decisions are authoritative in the Attempt Ledger,
  active spec and hosted artifacts.

## Current decision

Detector V2 is **Candidate Graph + Event-Sourced Recognition**. Skip=6 remains experimental.
Carney identity, Source Raw PRZ, M4 methodology and Outcome Engine remain frozen.

## Gate 2

Before production promotion:
- independent rule Oracle/full-label validation;
- synthetic-in-real A-share noise;
- blind holdout;
- expanded zero-mutation streaming gate.
