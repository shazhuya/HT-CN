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
detector correctness against independent ground truth. Candidate counts, coverage and green CI are
not substitutes for TP/FP/FN, recall, precision or node error.

The user explicitly requires the project to stop expanding peripheral product features and focus on
the core question: can HT-CN recover the correct harmonic swing nodes from raw OHLC without future
leakage or uncontrolled false positives?

## Objective

Build a detector-correctness program before changing recognition algorithms:

1. freeze 04aa3573... as the V1 production baseline;
2. define machine-readable ground truth and one-to-one prediction matching;
3. report recall, precision, F1, exact-node rate and per-node bar error;
4. attribute authoritative misses to pivot, candidate-window or rule stages;
5. add controlled positive, adversarial negative and later synthetic-in-real corpora;
6. add streaming/future-tail invariance gates;
7. compare V1 authoritative, Pine R3.4 behavioral and future experimental detectors on the same corpus;
8. do not change Carney identity, Source Raw PRZ, M4 methodology or Outcome Engine to improve benchmark scores.

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


## A-20260925-0090-001 — Gate 0 correctness baseline

- validated head: `0d193843f5600514cca874eff1f726586a9f1d78`
- workflow: `36163533018 / #3018`
- result: success
- corpus: `recognition-correctness-gate0-v3`
- corpus SHA-256: `c0104be8801dff56eca1828e48d6e413b0ca6ecb4167c5a80e0224a8d06999cc`
- controlled clean positives: authoritative 10/10 exact.
- bounded minor-swing stress matrix: authoritative 0/100; all 100 losses were `candidate_window_missing` while the truth pivots existed.
- experimental bounded graph + unchanged canonical classifier: 100/100 exact, 0 false positives on the stress matrix.
- controlled hard negatives: graph 10/10 clean rejection.
- future replacement regression: final-history pivot collapse can erase an earlier valid geometry; event-sourced streaming graph preserves the first knowable completed event.
- interpretation: the primary proven bottleneck is consecutive-pivot candidate construction, not the frozen Carney classifier or PRZ mathematics.
- limitation: this is controlled ground truth, not a real-market semantic accuracy claim.

### Gate 1 pre-registered interpretation

Before observing Gate 1 results, the following decision rules are frozen:

- if depth-1/depth-2 remain strong but depth-3 recall collapses, treat the bounded skip budget as the
  next candidate-generation bottleneck; do not relax Carney ratios or PRZ;
- if multi-scale recall improves but false positives/predictions-per-case rise materially, add
  graph-level dominated-path pruning and cross-scale geometry dedupe before increasing search depth;
- if independent invalid-B/invalid-C/invalid-D negatives produce false positives, fix graph path
  admissibility or dedupe first; canonical identity remains frozen;
- streaming confirmed-history mutation must remain zero before any production promotion.

### Next gate

Do not integrate the experimental graph into production yet. Expand adversarial coverage with:
- randomized minor-swing amplitude/time placement;
- near-boundary hard negatives;
- multi-scale graph pressure/duplicate control;
- batch future-tail invariance;
- synthetic-in-real A-share noise;
- blind holdout.


## A-20260925-0090-002 — Gate 1 adversarial graph + streaming validation

- validated head: `07d2e46f38f034a9780497d72614a804e5fcb823`
- workflow: `36166500765 / #3035`
- result: success
- artifact: `10878190860`
- corpus: `recognition-adversarial-gate1-v1`
- corpus SHA-256: `d1ca728306758a2ee2daf9bb1e4ec2e43cdf243ea034ce58ad7e56cd91cb8490`
- randomized positives: 120 controlled XABCD cases across five standard families, bullish/bearish,
  randomized minor-swing amplitude/time placement and 1/2/3 contaminated legs.
- skip budget 4: depth-1 = 40/40 exact, depth-2 = 40/40 exact, depth-3 = 0/40.
- skip budget 6: 120/120 primary structures recovered exactly, node MAE 0 bars.
- multi-scale S3/S5/S8 produced the same primary recovery and no additional candidate explosion on
  this corpus.
- independent clean near-miss negatives: invalid-B 10/10 rejected, invalid-C 10/10 rejected,
  invalid-D 10/10 rejected under both skip budgets and both scale configurations.
- one additional Bat candidate appeared in one contaminated positive frame. Inspection shows that
  the inserted minor pivot itself creates a second canonical-valid nested Bat
  (X/A/B/C/D = 30/110/190/324/350); therefore positive-frame extra predictions are not automatically
  valid false-positive labels. Gate 2 must use independent/full labels for precision.
- future-tail stress: final-history collapse erased the original confirmed pattern in 24/24 cases;
  event-sourced streaming preserved 24/24 first-knowable patterns with confirmed-history mutation 0.
- interpretation: Candidate Graph + Event-Sourced Recognition are now required V2 architecture
  elements. `max_total_skips=4` is empirically too shallow; skip=6 is the current experimental
  baseline, not a production default.
- limitation: controlled ground truth only; no real-A-share semantic accuracy or profitability claim.

### Gate 2

Before production promotion:
- build an independent rule oracle/full-label path so nested valid structures are not mislabeled FP;
- inject known structures into real A-share noise/background (synthetic-in-real);
- measure graph candidate pressure and primary-node recovery under gaps/wicks/volatility changes;
- add blind holdout seeds/time blocks;
- keep streaming history mutation at zero.
