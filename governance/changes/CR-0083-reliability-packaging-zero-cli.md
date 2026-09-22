# CR-0083 — M9.5 Reliability, Packaging & Zero-CLI Operation

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 86a618d20d47907e82a5557d6df791b8612dbcde
target: main
milestone: M9.5
work_branch: m9/reliability-packaging-zero-cli-v1

## Objective

Turn the M9.1–M9.4 services and workbench into a product runtime that can be installed, started, updated and recovered without daily command-line operation, while preserving M4 evidence provenance through a verified packaged release identity.

## Scope

- add a verified release identity manifest for packaged installs and make evidence code identity use it only when no Git repository is available;
- keep dirty Git worktrees fail-closed and never allow a package manifest to override a dirty checkout;
- add one product supervisor for API, static Web, market-data service, harmonic runtime and background evidence service with restart/backoff/status;
- serve built Web assets in daily use so Node/Vite is not required after packaging;
- productize backup, restore and pre-update snapshot handling for mutable research/product state;
- add deterministic release-package creation and verification;
- replace daily multi-console startup with one-click/background start and explicit stop/recovery entry points;
- expose supervisor/release/backup health through read-only product status and Chinese diagnostics;
- add hosted tests for release identity, restart behavior, backup/restore, package verification and zero-CLI browser/runtime contracts.

## Fixed boundaries

- no changes to frozen M4 capture methodology or Outcome Engine;
- no change to Carney/Source/harmonic/lifecycle semantics;
- no automatic trading;
- no historical M7 backfill;
- packaged release identity must be hash-verified and must not weaken Git clean-worktree provenance;
- M8/ISSUE-0066 remain claims-only;
- no routine user-computer dependency for development or validation.

## Acceptance

See specs/m9-phase-5-reliability-packaging-zero-cli.md.

## Ready-to-merge evidence

- PR #71 run #2571: Project OS, Source Coverage, Ruff 0/0, 982 Python / 0 warnings and Web green.
- Release ZIP SHA-256: 8b6852e30dc0c85d17ba073357f063d55d457a9b35a784142e6ce97cfaf0aa35.
- Extracted package had no .git and passed M4 methodology 37/37, Outcome Engine 4/4 and product-supervisor preflight.
- 28/28 browser, Phase18, Phase21 and canonical checkout 37/4 gates passed.
- Formal artifact: 10695889957 / sha256:d8a8b9568d28b7386c18168c3310eaee1e162c065ae01728da93859a4c351858.
- Final merge still requires an exact ledger-bearing PR rerun and canonical-main post-merge validation.
