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

Detector V2 is now **Hierarchical Swing Graph + Event-Sourced Recognition**. The original bounded
step-{1,3} graph remains as a comparison baseline. The hierarchical graph may span odd pivot gaps
up to 7 only when both selected endpoints dominate skipped pivots of the same kind, with total skip
budget bounded at 12. Carney identity, Source Raw PRZ, M4 methodology and Outcome Engine remain frozen.

## Gate 2 — validated

Hosted run `36167742120` / artifact `10878004217`:
- independent standard-XABCD rule oracle imports no production rule/evaluator/scanner/discovery/engine;
- 121/121 production graph predictions agreed with the oracle;
- 30 invalid-B/C/D negatives remained 0/30 predictions;
- one contaminated positive frame contains two oracle-valid nested geometries, confirming that one-primary-truth precision alone can mislabel a valid nested candidate.

## Gate 3 — validated

The first synthetic-in-real fixture version was invalid because its pre-X/post-D guards allowed X/D
to fail as actual turning pivots; that result was retained as failed benchmark evidence and was not
used to judge the detector.

Corrected fixture v2 established that the old bounded step-{1,3} graph was still too narrow:
- development: 32/72 exact (44.44% recall);
- blind holdout: 5/18 exact (27.78% recall);
- truth nodes existed on at least one configured scale in 100% of development/holdout cases;
- recent-20 frontier coverage was 100%;
- step-{1,3} compatibility existed in only 47.22% development / 44.44% holdout cases;
- minimum viable max leg step had median 5, with development reaching 7.

Detector V2 therefore added a hierarchical swing graph: odd leg steps 1/3/5/7 are permitted only
when selected endpoints dominate every skipped same-kind pivot inside the leg, and total skipped
pivots are bounded at 12.

Hosted full CI run `36209803011` / Gate 3 artifact `10894024765`, independently replicated by
fast run `36209803059` / artifact `10895162161`:
- development: 72/72 exact, 100% injected-truth recall, 2 unmatched extra canonical predictions,
  1.0278 predictions/case;
- blind holdout: 18/18 exact, 100% injected-truth recall, 1 unmatched extra canonical prediction,
  1.0556 predictions/case;
- every Gartley/Bat/Butterfly/Crab/Deep Crab family in both splits reached 100% injected-truth recall;
- event-sourced streaming preserved 12/12 development and 12/12 holdout truths;
- all pre-registered Gate 3 checks passed;
- Ruff debt remained zero, 1065 Python tests and Gate 0/1/2 regressions passed.

This does **not** establish real-market semantic precision or profitability. Gate 4 is a disagreement
audit on unmodified real A-share history before any production integration.


## Gate 4 pivot — completion semantics reset

Unmodified real-market audit changed the implementation plan without changing Carney/source rules.

Facts:
- after fail-closing Alternate Bat, strict retrospective five-pivot completed XABCD produced 0 standard Gartley/Bat/Butterfly/Crab/Deep-Crab matches on the frozen 45-symbol A-share audit;
- structural candidate supply was not zero: the audit observed 13,951 legacy five-point candidates and 58,337 hierarchical-V2 candidates;
- D/XA was the dominant final identity rejection and 135 V2 candidates were one-reason near misses;
- hierarchical XABC projected 1,745 source-cleared standard structures; 976 later overlapped Source Raw PRZ;
- with a full 180-bar observation horizon, 887/1515 (58.55%) reached Source Raw PRZ;
- canonical `observe_source_execution()` recorded 739 Source Terminal Price Bars overall and 682/1515 (45.02%) on full-horizon cases;
- only 157/739 (21.24%) canonical Source Terminals were within ±3% of the nominal D/XA ratio, so simply widening exact-D tolerance to 3% is rejected.

Decision:
1. **Structure identity** = first-knowable Hierarchical XABC using source-cleared family constraints.
2. **Projected completion zone** = frozen Source Raw PRZ; no new PRZ math.
3. **Completed event** = event-sourced Source Terminal-side test after the projection is knowable.
4. **Retrospective D pivot / exact D-XA** = geometry audit only, not the sole production completion gate.
5. **Invalidation/expiry is mandatory** before production: a broken/expired XABC may not later resurrect merely because price revisits PRZ.
6. Alternate Bat and Five-Zero remain fail-closed/quarantined.

### Single-mainline contract

Until Gate 4B is green, the only allowed product-development work is:
`raw OHLC -> pivots -> Hierarchical XABC -> Source Raw PRZ -> invalidation/expiry -> Source Terminal -> dedupe/audit`.

Do not work on UI, AI explanation, win-rate/alpha, Outcome Engine, Daily Review, installers, new indicators or broad product features. A change that does not improve recognition correctness, time-of-knowledge or false-positive control is out of scope.
