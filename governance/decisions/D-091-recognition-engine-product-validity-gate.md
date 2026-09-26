# D-091 — Harmonic recognition trustworthiness is the highest HT-CN product-validity gate

status: active
date: 2026-09-26

## Decision

HT-CN permanently treats the harmonic recognition engine as the **highest-priority product-validity gate**.

If raw market data cannot be converted into correct, time-valid harmonic structures with controlled false positives, every downstream capability consumes untrustworthy input. In that state PRZ/lifecycle/Outcome/statistics/AI explanation/UI/automation may be technically functional, but the product has no meaningful harmonic-trading research value.

Therefore, whenever recognition trustworthiness is unresolved:

1. recognition correctness has priority over UI, Outcome, win-rate/alpha, AI explanation, new indicators, packaging and other peripheral product work;
2. success must be measured by fixed-ground-truth Recall/Precision, node correctness, no-lookahead/history immutability, completion semantics, invalidation/expiry, duplicate control and real-market false-positive evidence;
3. more candidates, visible drawings, more code or more tests are not substitutes for correctness;
4. Carney Source Identity and Source Raw PRZ may not be relaxed to manufacture recall;
5. production promotion requires blind/real-market evidence; unresolved recognition defects keep the recognition gate open even if Stable runtime engineering is otherwise mature;
6. every blank-session/bootstrap handoff must state the current Recognition Gate and blocker before choosing the next development task.

## Current architecture consequence

The current recognition mainline is:

`Raw OHLC -> confirmed Pivot Events -> Hierarchical XABC -> frozen Source Raw PRZ -> validity/invalidation clock -> event-sourced Source Terminal completion -> dedupe/false-positive audit`.

Retrospective right-confirmed D geometry remains useful as audit/quality evidence but must not replace observable Source Terminal timing as the sole completion gate.

## Rationale

The project previously accumulated substantial product/governance/UI/lifecycle infrastructure while the detector could still miss meaningful harmonic structures. Gate 0-4 evidence later proved that consecutive-pivot candidate construction and retrospective exact-D completion semantics could suppress real structures even when downstream systems were functioning.

D-091 prevents recurrence: **if recognition is wrong, the rest of HT-CN is downstream decoration rather than a trustworthy harmonic system.**
