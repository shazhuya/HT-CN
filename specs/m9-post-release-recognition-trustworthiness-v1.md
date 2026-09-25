# M9 post-release — Recognition trustworthiness v1

status: planned
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
