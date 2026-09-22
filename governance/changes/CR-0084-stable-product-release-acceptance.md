# CR-0084 — M9.6 Stable Product Release Acceptance

status: planned
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 42950efe26dea85fe11ea7484e3aa7f59802c32b
target: main
milestone: M9.6
work_branch: m9/stable-product-release-v1

## Objective

Close M9 with a versioned stable HT-CN product release whose automated data, harmonic runtime, workbench, background evidence, recovery and zero-CLI contracts are machine-verified and documented.

## Scope

- define HT-CN Stable v1.0.0 as a product-runtime release, not a statistical-performance claim;
- unify Python/API/product release version identity;
- add a machine-readable Stable Product Contract;
- add a stable-release acceptance engine/report that consumes the verified M9.5 release-package report;
- require M9.0-M9.5 closed and all stable-product definition gates satisfied;
- permit ISSUE-0066 to remain open only while win-rate/alpha/profitability/statistical-significance/calibration claims remain explicitly unavailable;
- ship operator runbook, recovery contract and v1.0.0 release notes inside the release package;
- add stable-version browser/API acceptance;
- upload the verified release ZIP and stable acceptance report as formal main-release artifacts;
- create the final canonical stable release record after merge/main validation.

## Fixed boundaries

- no change to Carney identity, Source Raw PRZ, lifecycle or frozen M4/Outcome semantics;
- no automatic trading;
- no historical M7 backfill;
- ISSUE-0066 remains claims-only and non-blocking for product release;
- FIVE_ZERO stays quarantined and Alternate Bat stays fail-closed;
- no routine user-computer dependency.

## Acceptance

See specs/m9-phase-6-stable-product-release-acceptance.md.
