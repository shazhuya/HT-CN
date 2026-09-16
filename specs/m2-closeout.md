# M2 Closeout — Harmonic Core / Evidence Layer

Date: 2026-09-16

## 1. Closeout decision

M2 has reached its engineering and research closeout boundary. Do not keep extending M2 by mining more retrospective thresholds from already-consumed historical datasets.

The original M2 scope (`Pivot / Fibonacci / Pattern / PRZ Core`) is complete and has been expanded beyond the initial roadmap to include the execution-evidence foundations needed by the later workbench:

- confirmed multi-scale Pivot/Swing with right-side confirmation and no lookahead;
- XABCD families: Gartley, Bat, Alternate Bat, Butterfly, Crab, Deep Crab;
- standalone AB=CD;
- Shark 0XABC and 5-0 schemas;
- pattern-specific PRZ and geometry audit;
- completed vs forming/no-lookahead projections;
- Reaction vs. Reversal lifecycle evidence;
- source-aligned Terminal Price Bar;
- Type-I targets / retest / Type-II evidence separation;
- real A-share QFQ research calibration and robustness work;
- frozen 45-symbol Holdout and disjoint 60-symbol external replication;
- append-only prospective Type-I registry beginning after the 2026-09-15 retrospective cutoff.

## 2. Frozen scientific boundaries

The following are not reopened by later milestones unless a new versioned research protocol explicitly supersedes them:

1. Carney identity ratios and pattern schemas.
2. Pattern-specific raw PRZ geometry.
3. Historical Holdout and external-replication results, both consumed/closed.
4. The distinction between geometry score and probability: geometry score is never a success probability.
5. A-share context may modify execution/readiness/tradeability, but must not rename, rescue, delete, or geometrically alter a source-valid harmonic identity.
6. Prospective registry observation is descriptive. No optional-stopping significance checks or dynamic success-probability output are allowed.

## 3. M2 acceptance gate

The authoritative local closeout command is:

`运行M2综合验收.bat`

It must cover:

1. deterministic Python/Web/API/browser QA;
2. real local QFQ harmonic scan;
3. reaction/retest/RSI audit;
4. cross-scale Pivot robustness;
5. real A-share Golden Case candidate mining;
6. integrity verification of the frozen Type-I Holdout and independent external replication artifacts without recomputing them;
7. initialized local-dataset health.

The M2 acceptance command must **not** mutate the prospective registry. Prospective evidence collection remains a separate append-only operational flow.

GitHub CI is the repository-level gate. The latest M2 head must pass deterministic tests, web build, and the autonomous real-A-share regression/evidence checks before merge.

## 4. Prospective registry operating rule

From 2026-09-16 onward, after M1 daily market-data maintenance, run:

`运行M2前瞻Type-I登记.bat`

The registry preserves what was observable at the time. Registered events are not deleted on later rescans. Events first discovered after their T+5 prospective window remain audit backfills and are permanently excluded from a future prospective primary evaluation.

A future confirmatory analysis is **not** M2 closeout work. Before inspecting a new prospective endpoint for inference, create a separate versioned preregistration with a fixed stopping rule and statistical method.

## 5. What moves to M3

M3 is not another geometry rewrite. It is productization of the already-built core into an A-share trader-readable workbench.

Primary M3 goals:

- make the first screen answer `现在在哪 / 先看哪 / 到了再看哪` before exposing deep audit detail;
- present completed, forming, PRZ test, reaction, retest and Type-II states as a coherent visual lifecycle;
- keep XABCD/0XABC/5-0 geometry, node values, PRZ and invalidation visually anchored to K-lines;
- distinguish source geometry, statistical evidence, and A-share execution context by explicit layers;
- reduce audit/research clutter in the default view while retaining drill-down evidence;
- harden responsive layout and Playwright visual/interaction regression;
- preserve Chinese-first wording and A-share terminology;
- never generate or execute trades.

M3 may consume M2 outputs but must not mutate their source identity or frozen evidence artifacts.

## 6. Deferred work

The following are intentionally outside M2 closeout:

- a new prospective confirmatory test before its stop rule is preregistered;
- full A-share environment / priority ranking (M5);
- whole-market scanner (M7);
- minute-data cache (M8);
- automatic trade execution (out of project scope).
