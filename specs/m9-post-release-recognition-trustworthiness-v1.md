# M9 post-release — Recognition trustworthiness v1

status: validation_green
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
