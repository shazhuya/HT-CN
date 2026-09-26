# M9 post-release — Recognition trustworthiness v1

status: implementing
change: CR-0090

## Problem

CR-0089 acceptance establishes practical recognition availability, not semantic detector accuracy.
This spec introduces the missing correctness layer while preserving Stable production behavior.

## Benchmark tasks

### completed_xabcd

Input: raw OHLC containing a known completed standard XABCD structure.

Ground truth:
- pattern id;
- direction;
- labels X/A/B/C/D;
- exact node indices.

Prediction source:
- canonical authoritative `scan_frame`.

### projected_xabc

Input: raw OHLC containing a known X/A/B/C prefix.

Ground truth:
- pattern id;
- direction;
- labels X/A/B/C;
- exact node indices.

Prediction source:
- retained Pine R3.4 behavioral detector.

These tasks are reported separately. A projected XABC prediction is not credited as a completed
XABCD identity.

## Matching

Predictions are matched one-to-one to truths. One truth can credit at most one prediction.
Compatibility requires:
- same pattern id;
- same direction;
- same ordered labels;
- same node count.

Reports expose:
- exact match;
- tolerant match at predeclared bar tolerance;
- absolute bar offset for every node.

Unmatched predictions are false positives. Unmatched truths are false negatives.

## Required metrics

- truth count / prediction count;
- TP / FP / FN;
- precision / recall / F1;
- exact-node match rate;
- tolerant-node match rate;
- mean absolute node error;
- node error by label when available.

## Authoritative miss attribution

For known completed XABCD truth, the diagnostic path is:

1. `pivot_missing` — expected nodes cannot all be recovered on one configured pivot scale;
2. `candidate_window_missing` — pivots exist but no exact XABCD candidate window is generated;
3. `rule_rejected` — exact candidate exists but expected family does not pass identity;
4. `accepted` — expected family and exact nodes are emitted.

This attribution is diagnostic only and cannot mutate identity.

## Corpus policy

The initial deterministic corpus is a smoke baseline:
- source-shaped standard XABCD positives in bullish and bearish orientation;
- a small set of adversarial near-miss negatives;
- deterministic OHLC rendering with fixed parameters.

It is not sufficient for a real-market accuracy claim.

Later gates must add:
- larger independent synthetic corpus;
- hard negatives around every boundary;
- synthetic-in-real A-share noise;
- metamorphic invariants;
- streaming/future-tail invariance;
- blind holdout;
- real-market disagreement audit.

Changing corpus semantics requires a new corpus version/fingerprint. Detector tuning may not
silently change the test distribution.

## Frozen boundaries

This work must not modify:
- M4 capture methodology;
- M4 Outcome Engine;
- Source Coverage freeze;
- canonical Source Raw PRZ;
- CARNEY_RULES to rescue detector recall;
- Five-Zero/Alternate-Bat production status.


## Gate 0 evidence — 2026-09-25

Hosted run `36163533018` validated corpus
`recognition-correctness-gate0-v3`
(`c0104be8801dff56eca1828e48d6e413b0ca6ecb4167c5a80e0224a8d06999cc`).

The controlled result isolates candidate generation:
- clean authoritative XABCD: 10/10 exact;
- minor-swing matrix authoritative XABCD: 0/100;
- all 100 misses: `candidate_window_missing`, not `pivot_missing`;
- bounded graph candidate generation + unchanged canonical classifier: 100/100 exact;
- hard-negative graph false positives: 0/10.

This is sufficient to reject the consecutive-five-pivot candidate assumption as the sole production
completed-XABCD path. It is not sufficient to promote the experimental graph to production.


## Gate 1 evidence — adversarial graph depth and time-of-knowledge

Hosted run `36166500765` / artifact `10878190860` validated the deterministic
`recognition-adversarial-gate1-v1` corpus
(`d1ca728306758a2ee2daf9bb1e4ec2e43cdf243ea034ce58ad7e56cd91cb8490`).

Observed:
- skip=4 recovers all one- and two-minor-pair cases but 0/40 three-pair cases;
- skip=6 recovers 120/120 primary structures exactly with node MAE 0;
- 30 independent invalid-B/C/D clean negatives remain fully rejected;
- multi-scale S3/S5/S8 does not increase candidate count on this controlled corpus;
- a single additional candidate in a positive frame is itself canonical-valid nested geometry, so
  one-primary-truth precision is not a valid semantic FP estimate for contaminated positive paths;
- forced same-kind future replacement makes final-history collapse erase 24/24 earlier patterns,
  while event-sourced streaming preserves 24/24 with zero confirmed-history mutation.

Decision:
- Candidate Graph and Event-Sourced Recognition are mandatory for Detector V2;
- skip=6 remains experimental until synthetic-in-real + blind/full-label precision gates pass;
- canonical Carney identity and Source Raw PRZ remain frozen.


## Gate 2 evidence — independent rule oracle

Hosted run `36167742120` validated an oracle that imports no production rule/evaluator/scanner/
discovery/engine implementation. Production graph predictions agreed with the oracle 121/121 on
positive predictions, while 30 invalid-B/C/D negative cases produced zero production/oracle-valid
predictions. One contaminated positive frame contained more than one oracle-valid nested geometry,
so single-primary-truth precision cannot automatically classify every extra canonical geometry as a
false positive.

## Gate 3 evidence — synthetic-in-real A-share noise + blind holdout

The initial fixture was rejected because X/D were not guaranteed to be actual turning pivots. The
corrected fixture freezes real A-share bar texture from the 45-symbol QFQ research snapshot set
(cutoff 2026-09-15), uses a fixed SHA256-ranked 9-symbol holdout, and requires injected truth nodes
to be real detected pivots before detector quality is interpreted.

With the corrected fixture, the old step-{1,3} bounded graph recovered 32/72 development truths and
5/18 holdout truths. Diagnostics showed:
- truth-node presence on at least one scale: 100% / 100%;
- recent-20 frontier coverage: 100% / 100%;
- step-{1,3} compatibility: 47.22% / 44.44%;
- minimum viable max leg step median: 5; development maximum: 7.

The experimental hierarchical swing graph therefore uses:
- odd leg step <= 7;
- total skipped pivots <= 12;
- selected endpoints must dominate every skipped same-kind pivot inside the leg;
- unchanged canonical XABCD classifier;
- event-sourced first-knowable streaming births.

Hosted run `36209803011` / artifact `10894024765` passed:
- development: 72/72 exact, recall 1.0, exact-node rate 1.0, 1.0278 predictions/case;
- blind holdout: 18/18 exact, recall 1.0, exact-node rate 1.0, 1.0556 predictions/case;
- development streaming: 12/12 preserved;
- holdout streaming: 12/12 preserved;
- all Gate 3 thresholds green.

Fast workflow run `36209803059` / artifact `10895162161` independently reproduced Gate 3 so
recognition experiments no longer wait behind the entire product CI pipeline.

Boundary: this is controlled known-truth recovery under frozen real-market texture, not a claim of
real-market semantic precision, win rate, alpha or profitability. Production promotion requires a
Gate 4 disagreement audit on unmodified real A-share history.


## Gate 4 evidence and adjusted recognition architecture

Gate 4 on unmodified frozen A-share history showed that the remaining blocker is not merely candidate recall.
The retrospective five-pivot classifier can generate many structural candidates but effectively no
source-cleared standard completed XABCD because completion is gated by an exact D/XA point.

Independent real-market diagnostics found 1,745 source-cleared Hierarchical-XABC projections.
Canonical Source Execution later observed 739 Terminal Price Bars; among cases with a full 180-bar
horizon, 682/1515 (45.02%) reached Source Terminal. Only 21.24% of those terminals lay within ±3%
of the nominal D/XA ratio. Therefore ±3% exact-D tolerance is not the solution.

### Detector V2 architecture — revised

`Raw OHLC -> confirmed pivot events -> Hierarchical XABC -> frozen Source Raw PRZ -> active validity clock -> Source Terminal completion`

Required properties:
- XABC birth is first-knowable/event-sourced; no future pivot may create an earlier birth;
- only source-cleared standard families are production-eligible;
- Source Raw PRZ remains frozen;
- completion is the canonical Source Terminal-side event, not retrospective exact-D equality;
- explicit invalidation/expiry must stop dead patterns from resurrecting;
- exact/right-confirmed D geometry is retained as a retrospective quality/audit field;
- duplicate/nested completion events must be controlled before production promotion.

### Gate 4B release gate

Production integration is forbidden until all pass:
- event-sourced XABC/Source-Terminal unit and streaming tests;
- no-lookahead / future-tail invariance;
- invalidation and expiry tests with zero resurrection;
- unmodified real-market density/duplicate/false-positive audit;
- blind holdout;
- full Gate 0/1/2/3 regression with source-conflict families fail-closed.

No UI, outcome, win-rate or auxiliary-indicator work belongs in Gate 4B.


## Gate 4B closeout checkpoint — 2026-09-26

Latest validated head before closeout: `110089e1d3e285b6687eca6769033e6da9efc649`.

Hosted validation:
- full HT-CN CI `36252453523`: success;
- Recognition Gate 3 Fast `36252453534`, artifact `10909542800`: success;
- Recognition Gate 4B Fast `36252453531`: success;
- Source Completion artifact `10909996357`;
- Pine differential artifact `10910090853`.

Recognition facts now frozen for handoff:
- D-091 remains the highest product-validity rule; peripheral work stays frozen.
- Event-sourced completion is XABC birth -> frozen Source Raw PRZ -> actual PRZ-contact Terminal, with C-extreme invalidation, 180-bar expiry and no resurrection.
- Current production-eligible Source Completion cap is `max_leg_step=7 / max_total_skips=8`; 12 skips remain research-only.
- Latest 45-symbol real-market report: 4,424 projections, 991 completed, 3,222 invalidated, 165 expired, 46 active, zero exact duplicate completions and 828 deduped market Terminal events.
- Gate 3 capacity audit: research 7/12 = 72/72 development + 18/18 blind; current 7/8 = 65/72 (90.28%) + 18/18; tested 5/10 = 68/72 (94.44%) + 18/18 and is the smallest tested 90%+/90%+ capacity.
- Pine R3.4 remains a disagreement miner, not truth; matched-scale/consecutive ablations must not be used as a direct accuracy score.

Next gate: **Gate 4C — Production Graph Capacity & Precision Selection**.
Compare current 7/8 against 5/10 and only necessary neighboring capacities on the same frozen real-market corpus. Select the smallest defensible cap using known-truth recall plus real-market candidate/collision pressure and high-information adjudication. Do not relax Carney identity/Source Raw PRZ and do not resume peripheral product work.
