# CR-0069 — M6.4 Repository Governance

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.4

## Objective

Close the repository-governance phase without changing harmonic Source truth, M4 methodology,
Outcome Engine, market-data semantics, product trading semantics, or empirical claims.

## Current facts

1. historical stacked M5 pull requests are already closed/superseded under CR-0065;
2. pytest warning budget is already zero and CI fails on warning growth;
3. canonical main now enforces configured mutable Ruff observed=0 / budget=0; ISSUE-0068 is closed after full PR and post-merge validation;
4. GitHub branch metadata reports `main protected=false`;
5. repository rulesets currently return an empty set;
6. the connected GitHub App receives HTTP 403 for the branch-protection endpoint and exposes no
   administration write action, so server-side protection cannot be enabled from this execution path.

## Must solve

1. reduce repository-wide Ruff debt in bounded, test-backed mechanical batches and lower the frozen
   budget after each verified reduction;
2. make the final Ruff baseline explicit and non-growing;
3. preserve warning budget zero;
4. record the exact server-side protection/ruleset evidence and permission boundary without
   pretending protection is enabled;
5. ensure Project OS, formal release, post-merge main validation and continuation artifacts agree;
6. leave M6.5 as the next task only after M6.4 internal governance gates are complete.

## Acceptance

See `specs/m6-phase-4-repository-governance.md`.

## Non-goals

No harmonic detector/PRZ/lifecycle changes, no M4 capture/outcome changes, no universe expansion,
no BSE enablement, no market-data repair, no trade execution and no profitability/statistical claims.


## Progress evidence

- Hosted branch CI run 35463650834 on head `b30c9d7043ff349302f6c816ff71f6d613f3f630` passed Project OS, mutable Ruff `0/0`, 890 Python tests, zero pytest warnings and Web build.
- D-070 preserves immutable M4 capture/outcome components under the 37/37 and 4/4 byte-level freeze guards instead of lint rewriting them.
- D-071 records exact-path/exact-rule behavior-sensitive legacy lint exceptions in `governance/QUALITY_EXCEPTIONS.json`; wildcard exceptions are prohibited.
- Temporary autofix/report workflows were removed from the candidate branch.
- Full PR-only browser/Phase18/Phase21/M4 freeze gates remain required before ISSUE-0068/M6.4 closure.
- GitHub server facts remain: main protected=false; repository rulesets empty; branch-protection detail is inaccessible to the connected integration with HTTP 403; no administration write action is exposed.


## Full PR validation

PR #53 head `9f19ba55ab389bd13e5084a21d93c20b85825eb6` passed workflow
`35464886662` / run #2328:

- Project OS: success
- mutable Ruff: 0 / budget 0
- Python: 890 passed
- pytest warnings: 0
- Web build: success
- existing browser acceptance: 24 passed
- Phase18 browser/evidence: valid
- Phase21 dynamic browser/evidence: valid
- M4 methodology freeze: frozen_match, 37 components
- Outcome Engine freeze: frozen_match, 4 components
- evidence artifact: 10591125410
- artifact digest: sha256:1347bf1921af268aea8ae1b9e612129c149d891ff3c2df90b19293f9be271aa7

The candidate is ready for one final ledger-bearing validation before merge.


## Final closeout

- Final unchanged candidate: `ae0bbf1fb6ba1f8868b85a02bd81cb49c0aece54`
- Final validation PR: #54
- PR workflow: `35465432172` / #2344 — success
- Merge commit: `c0f287890218318d19e9b745cb03663e4e89205b`
- Canonical main workflow: `35465565858` / #2345 — success
- mutable Ruff: `0 / 0`
- Python: `890 passed`
- pytest warnings: `0`
- browser acceptance: `24 passed`
- Phase18: valid
- Phase21: valid
- M4 methodology: frozen_match, 37 components
- Outcome Engine: frozen_match, 4 components
- formal-release artifact: `10590763591`, digest `sha256:16946d365501684653d36c9e446bdb70f7338bb7f02b6f99ace6782b4d9dfd40`
- continuation artifact: `10591570617`, digest `sha256:6c8aaaf722fa565a72662e80966c8693463dffe6cb29a79b84e26e459aafb655`

PR #53's stale GitHub Actions concurrency run was bypassed without changing candidate content by validating the identical SHA through PR #54.

ISSUE-0068 is closed. ISSUE-0063 remains explicitly `blocked_external_permission` under D-072 because GitHub server-side branch protection is still disabled and cannot be administered through the connected integration. This does not convert the external limitation into a false internal success claim.

M6.4 is closed and M6.5 Source Coverage Freeze becomes the next major task.
