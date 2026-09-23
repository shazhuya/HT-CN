# CR-0084 — M9.6 Stable Product Release Acceptance

status: closed
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

## Closeout receipt

- Final ledger-bearing PR #72 head `3db650b205e18109eb48432afa3f5a75b7277f4c` passed workflow 35813645376 / run #2602 with Stable v1.0.0 release package SHA-256 `6e90651c164549755cb5e74bc616ac9a39c92a7f09b0689223614118a402425c`; artifact 10730477219 / sha256:74d258bca513f648ff7f1e07b32178e92ac89f4bd1620718282b78282e53229a.
- PR #72 merged with ancestry preserved as canonical main commit `c8322ebb9461c8febf182a68c803692c29339b80`.
- Canonical main workflow 35813838510 / run #2603 passed 986 Python tests / 0 warnings, Web build, verified Stable v1.0.0 package SHA-256 `5909bd21f816e749a54475650b2b9d452137de3ff3e95fb8815dd5a6428036b9`, 29 browser tests, Phase18/21, M4 methodology 37/37, Outcome Engine 4/4 and final Stable acceptance status=ready.
- Canonical release artifact: 10730059043 / sha256:e9ab5cd8a6888fe73d0dadce62094e3cee772b30c825b1bef306650835c61fbb.
- Canonical continuation artifact: 10730483695 / sha256:55b611ac6e8f22a8e0725a7fa9283d9eb232c9189572b1d0bb9db9f3f1534960.
- M9.6 and M9 are closed as Stable v1.0.0 product-runtime completion. ISSUE-0066 remains claims-only; M7 continues in the background and M8 remains evidence-authorized only. No routine user-computer action is required.

## Post-closeout self-validation

- Closeout head `ef5dc03d2989313a9ee6679c1d62793d7e794015` / workflow 35814161493 / run #2604 passed Project OS, Source Coverage and Ruff 0/0, then stopped at 985 Python passed / 1 failed.
- The sole failure was release-ledger backward compatibility: `claims.private_m1_current_market_closeout_ready` was absent from the new Stable v1.0.0 release record.
- Stable release semantics are unchanged. The compatibility field is explicitly set to `false`; this release does not claim that Stable Product publication itself proves private-M1 market closeout.
- Formal gates were correctly skipped on #2604. Post-release maintenance remains blocked until the corrected canonical-main self-validation is green.
- Corrected closeout head `23eb9471d4f4e27d10a73781d13b2fc20dc5c0a6` / workflow 35814318855 / run #2605 passed the full canonical-main sequence: 986 Python / 0 warnings, continuation bundle, Web, Stable v1.0.0 package, 29 browser tests, Phase18/21, M4 37/37, Outcome 4/4 and Stable acceptance ready. Post-release blocker cleared.

