# CR-0084 — M9.6 Stable Product Release Acceptance

status: implementing
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 42950efe26dea85fe11ea7484e3aa7f59802c32b
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

## Planned candidate validation

- Run #2592 / workflow 35807165469 passed Project OS, Source Coverage, Ruff 0/0, 984 Python tests / 0 warnings, Web build, deterministic verified release package, 28 browser tests, Phase18, Phase21, M4 methodology 37/37 and Outcome Engine 4/4.
- Artifact: 10728416383 / sha256:66f224f8a4b9b50d70a895fbd9949e395aec79b83fb4553240db80de22315886.
- Release package SHA-256: b2066942156801eff235885c1e2dd657244dfff5d95a85e263019a8cf55140f1.
- CR-0084 is now activated; the exact activated candidate must rerun all formal gates including the new M9.6 acceptance step.

## Activated validation note

- Run #2594 failed only the Project OS Resume Pack compactness test at 30427 characters after Project OS, Source Coverage and Ruff 0/0 passed; Python result was 983 passed / 1 failed.
- PROJECT_STATE is intentionally compacted to hosted-validation references; detailed evidence remains here and in the Attempt Ledger. The 30000-character contract is unchanged.
