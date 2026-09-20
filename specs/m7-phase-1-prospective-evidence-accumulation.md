# M7.1 — Prospective Evidence Accumulation Control Plane

status: planned

## 1. Objective

Begin M7 by operating the already-frozen prospective evidence machinery from canonical `main`
and by exposing factual accumulation progress without introducing statistical or trading claims.

M7.1 is an operational/evidence-control phase. It does not redefine harmonic methodology.

## 2. Canonical-main capture boundary

An authoritative M7 capture may start only when all of the following are true:

1. the checkout is on branch `main`;
2. `git fetch origin main` succeeds immediately before capture;
3. local `HEAD` exactly equals freshly fetched `origin/main`;
4. the worktree is clean;
5. the frozen M4 methodology guard is `frozen_match` for all 37 components;
6. the frozen Outcome Engine guard is `frozen_match` for all 4 components;
7. a real private M1 catalog exists.

Failure of any preflight condition occurs before M1 update and before authoritative capture.

The historical branch `m4/real-a-share-validation-workflow` is no longer an accepted M7
collection origin.

## 3. Reused authoritative evidence path

M7.1 reuses the frozen pipeline in this order:

1. smart M1 update;
2. strict QFQ readiness;
3. authoritative M4 committed lifecycle capture;
4. evidence-chain health;
5. lifecycle transition report;
6. prospective observation report;
7. preregistered outcome-v2 snapshot;
8. evidence handoff bundle;
9. M7 accumulation status.

The M7 status report is derived and disposable. Authoritative evidence remains the committed M4
capture transaction chain plus the committed outcome snapshot chain.

## 4. M7 accumulation status

The report may expose factual counts and chronology, including:

- committed future capture count and dates;
- latest committed capture date;
- zero-candidate capture count;
- prospective outcome-enrolled candidate count;
- observation count;
- candidates that have ever disappeared from the scanner;
- candidates with observed Source Terminal;
- candidates with price-basis drift;
- maximum captured-snapshot follow-up depth;
- committed outcome snapshot count/latest as-of;
- latest outcome status counts;
- minimum/maximum traded market-path depth represented by the latest outcome snapshot.

It must not compute or expose:

- win rate or win/loss labels;
- expected return or profitability;
- alpha or benchmark excess return;
- p-values/significance tests;
- buy/sell ranking;
- entry, stop, position size, fees, or execution P&L.

## 5. ISSUE-0066 gate

M7.1 does not invent a sample-size threshold.

Until a separately reviewed and frozen statistical-inference protocol defines the required sample,
coverage, censoring, and inference conditions, the report must keep:

- `statistical_inference_allowed=false`;
- `alpha_inference_allowed=false`;
- `win_rate_inference_allowed=false`;
- `profitability_inference_allowed=false`;
- `issue_gate=ISSUE-0066`.

More observations are evidence accumulation, not automatic permission to make statistical claims.

## 6. Frozen boundaries

The following remain immutable:

- M4 capture methodology commit
  `c774c54928c33361952bf1a612a8555633449625` / 37 components;
- M4 Outcome Engine commit
  `9cbc0d3d30ac5f0a87748a39788cbee04a44bcc8` / 4 components;
- Source Coverage Freeze at M6.5;
- 5-0 production quarantine;
- Alternate Bat fail-closed state;
- BSE default-scope deferral.

## 7. Acceptance gates

M7.1 may become active only after a hosted branch workflow passes Project OS, Source Coverage,
Ruff/Python/Web, and both immutable M4 freeze guards.

M7.1 may close only after:

1. the canonical-main one-click M7 entry is merged;
2. status-report tests and all existing regression gates are green;
3. full PR browser/Phase18/Phase21 gates are green;
4. canonical-main post-merge validation is green;
5. governance Attempt/Decision/Issue/State/Milestone records agree;
6. the next M7 evidence-accumulation action is persisted in PROJECT_STATE.

A private M1 capture is not fabricated by hosted CI. When the implementation is merged, the next
real evidence append must be performed against the user's private M1 through the M7 one-click entry.
