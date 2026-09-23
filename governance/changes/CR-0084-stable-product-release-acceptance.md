# CR-0084 — M9.6 Stable Product Release Acceptance

status: planned
baseline_ref: main
baseline_head: 42950efe26dea85fe11ea7484e3aa7f59802c32b
work_branch: m9/stable-product-release-acceptance-v1
spec: specs/m9-phase-6-stable-product-release-acceptance.md

## Objective

Complete M9.6 by adding a machine-enforced Stable Product release acceptance gate, packaging the operator/recovery contracts, producing version-bound release evidence and closing the M9 productization mainline without waiting for ISSUE-0066 or additional natural M7 sample days.

## In scope

- machine-readable stable release contract;
- operator guide and recovery contract in the release package;
- M9.6 acceptance evaluator + CLI + deterministic tests;
- formal CI ordering and artifact upload;
- Project OS / M9.6 governance activation and final closeout;
- exact release package/head/version/digest evidence in Attempt ledger.

## Out of scope

- any new harmonic identity, ratio, PRZ, lifecycle or scoring rule;
- changes to frozen M4 capture methodology or Outcome Engine;
- M8 calibration authorization or statistical claims;
- 5-0/Alternate Bat support changes;
- automated trading execution;
- routine use of the user's computer.

## Acceptance criteria

1. Current M9.1-M9.5 closed state is preserved.
2. Stable release acceptance runs only after formal browser and 37/4 freeze gates.
3. Release package remains deterministic, verified, no-Git capable and excludes mutable/private market data.
4. Operator and recovery docs ship inside the release package.
5. ISSUE-0066 remains claims-only and cannot block M9.6.
6. New/edited Python is Ruff-clean and Python warnings remain zero.
7. Formal PR and canonical-main validation are green.
8. M9.6 closes with an append-only Attempt entry and a generated continuation bundle.

## Current implementation note

The container used by this agent cannot resolve `github.com` for direct `git clone`, but the connected GitHub integration has verified canonical main and supports repository writes/CI. This environment limitation is not a user-computer requirement and is not a project blocker.
