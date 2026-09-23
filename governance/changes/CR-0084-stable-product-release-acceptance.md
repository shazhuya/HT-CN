# CR-0084 — M9.6 Stable Product Release Acceptance

status: ready_to_merge
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

## Candidate convergence and formal validation

- PR #72 is the canonical M9.6 candidate because it binds Stable v1.0.0 across Python package, API, UI, release manifest and release documentation.
- PR #73 was independently audited and closed as superseded; its stricter ordering rule is retained here: M9.6 acceptance executes only after browser acceptance, Phase18/21 and both immutable M4 freeze guards succeed.
- PR #72 run #2586 / workflow 35758512194 passed Project OS, Source Coverage, Ruff 0/0, 986 Python tests / 0 warnings, Web build, verified no-Git release ZIP v1.0.0, 29 browser tests, Phase18, Phase21, M4 methodology 37/37 and Outcome Engine 4/4.
- Run #2586 release package SHA-256: 432fc4c37547402a434368c48ecdb26656586fc33684adf1197a3995ae2741f6.
- Run #2586 artifact: 10709575483 / sha256:e9090871f96a3f7b272a7a5a386de2839215055dbbc0eea53087dfec8ffa93b7.
- Because CI ordering changed after #2586, the new exact ledger-bearing candidate must rerun the full formal release gate before ready_to_merge.
- Exact convergence head `a7fb82e9468b17bbc0dab5dd5aab3b00ed4c92de` / run #2598 failed only the fixed Resume Pack compactness gate at 30158 characters after Project OS, Source Coverage and Ruff 0/0 passed; Python result was 985 passed / 1 failed. Keep the 30000-character gate and compact PROJECT_STATE instead of weakening validation.
- Exact convergence retry `fff4c02b535f89853170cd0fdcc59e715592c5a7` / run #2600 / workflow 35813397345 passed the full formal sequence with 986 Python tests / 0 warnings, Stable v1.0.0 release package SHA-256 `49d0df954b81bb04d7c73c5a6f08dd2714183ae7408351ad34a7e66f3465107a`, 29 browser tests, Phase18/21, M4 37/37, Outcome 4/4, then Stable acceptance status=ready. Artifact 10730757725 / sha256:e5e219deebefa55105bafacf1876ad29dea59891a9a211741bcb24254196b3bf.
