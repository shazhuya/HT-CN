# D-072 — GitHub server-side protection remains an explicit external-permission limitation

status: `active`

## Decision

M6.4 internal repository-governance closeout does not make a false claim that GitHub main branch
protection is enabled.

Observed server-side facts during M6.4:

- `main protected=false`;
- repository rulesets are empty;
- branch-protection detail access returns HTTP 403 `Resource not accessible by integration`;
- the connected GitHub integration exposes no administration write action.

Therefore ISSUE-0063 remains `blocked_external_permission`, but it does not block completion of
the repository-internal M6.4 gates that are actually controllable from this execution path.

## Compensating controls

Until an administrator enables server-side protection, HT-CN relies on repository-internal controls:

1. Project OS fail-closed state validation;
2. Ruff zero mutable-scope budget and zero warning budget;
3. PR-triggered formal-main-release-integrity;
4. 24 browser acceptance tests;
5. Phase18 and Phase21 browser/evidence verification;
6. M4 methodology 37/37 freeze guard;
7. Outcome Engine 4/4 freeze guard;
8. merge-commit ancestry preservation and post-merge canonical-main validation.

## Non-claim

This decision does **not** assert that branch protection or required checks are enforced by GitHub
server settings. A repository administrator may harden those settings later.
