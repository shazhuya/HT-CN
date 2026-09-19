# M6.4 — Repository Governance

status: ready_not_started

## 1. Objective

Finish the repository-integrity work needed before Source Coverage Freeze. This phase is governance
and quality only; it must not alter harmonic Source truth or research semantics.

## 2. Internal quality closeout

M6.4 must:

- keep pytest warning budget at zero;
- reduce the repository-wide Ruff debt from the inherited baseline through bounded mechanical fixes;
- lower `governance/QUALITY_BASELINE.json` only after the lower count is observed in hosted CI;
- keep all newly added or materially edited Python files Ruff-clean;
- preserve Project OS, Python, Web, browser, Phase18, Phase21 and both M4 freeze guards.

ISSUE-0068 may close only when the final accepted repository-wide Ruff baseline reaches zero, unless
a future explicit decision identifies a specific non-mechanical exception with evidence. M6.4 must
not silently normalize remaining debt.

## 3. Server-side main protection evidence

M6.4 must verify and persist the observable GitHub server-side state.

At phase start the observable facts are:

- branch metadata: `main protected=false`;
- repository rulesets: none;
- branch-protection detail endpoint: inaccessible to the connected GitHub App (HTTP 403,
  Resource not accessible by integration);
- no connector administration write action is available.

The phase must not claim that branch protection is enabled when it is not. If administration
permission remains unavailable, ISSUE-0063 remains an external-permission issue, but the exact
limitation must be recorded as an accepted external governance blocker rather than leaving the
repository's internal governance state ambiguous.

## 4. Ruff remediation method

1. first apply only Ruff's safe automatic fixes on the M6.4 branch;
2. never use `--unsafe-fixes` as a bulk operation;
3. run the full hosted gates after the safe-fix batch;
4. inspect remaining rule/file diagnostics;
5. repair non-auto-fixable violations in bounded reviewable batches;
6. after every green reduction, lower the frozen Ruff budget to the observed count;
7. finish at zero before ISSUE-0068 closes.

Temporary branch-only automation used to create mechanical fixes must be removed before M6.4 merge.

## 5. Acceptance gates

M6.4 may close only when:

1. Ruff repository-wide observed count is 0 and budget is 0;
2. pytest warnings remain 0;
3. Project OS integrity is green;
4. Python tests and Web build are green;
5. existing browser acceptance, Phase18 and Phase21 are green;
6. M4 methodology freeze remains 37/37 and Outcome Engine freeze remains 4/4;
7. server-side protection/ruleset state and permission boundary are recorded exactly;
8. ISSUE-0068 is closed;
9. ISSUE-0063 is either resolved by actual server-side protection or retained explicitly as
   blocked_external_permission with no false protection claim;
10. final PR and post-merge canonical-main validation are both green;
11. Attempt/Issue/State/Milestone/Decision records agree;
12. M6.5 Source Coverage Freeze becomes the next major task.

## 6. Non-goals

This phase does not change Source identity, raw PRZ, Source Clock, Reaction/Reversal, RSI BAMM,
5-0 quarantine, Alternate Bat fail-closed status, M4 evidence semantics, A-share universe semantics,
or trading execution behavior.
