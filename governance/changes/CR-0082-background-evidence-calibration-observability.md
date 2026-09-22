# CR-0082 — M9.4 Background Evidence, Calibration Boundary & Observability

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 64f65055576e7c7940f217e3e4f872db41528c12
target: main
milestone: M9.4
work_branch: m9/background-evidence-observability-v1

## Objective

Productize the established M7 prospective-evidence path as a background service so normal daily operation no longer depends on BAT/PowerShell, ZIP handoff or AI/manual acceptance, while preserving the frozen M4 capture/outcome semantics and keeping M8 statistical calibration fail-closed until explicit evidence authorization exists.

## Scope

- orchestrate the existing frozen methodology guard, Outcome Engine guard, M7 append precheck, QFQ readiness, authoritative lifecycle capture, evidence health, lifecycle transition, prospective observation, outcome-v2 and accumulation-status steps as a background service;
- use same-session idempotency and success watermarks so already-committed sessions do not rerun append-only work;
- keep transport ZIP creation and M7 evidence-bundle acceptance outside the normal daily product path;
- expose one machine-readable evidence-service status that separates operational faults from empirical insufficiency;
- expose an explicit M8 calibration gate that is disabled unless ISSUE-0066 is resolved and an explicit calibration authorization is present;
- add read-only API/product observability with Chinese diagnostics;
- add deterministic tests for healthy, idempotent, blocked, operational-fault and insufficient-evidence paths.

## Fixed boundaries

- no change to the frozen M4 capture methodology or Outcome Engine;
- no change to Carney ratios, pivots, Source Raw PRZ, lifecycle or harmonic identity;
- no 5-0 production enablement and no Alternate Bat relaxation;
- no win-rate, alpha, profitability or statistical-significance claim;
- no trading execution;
- no historical M7 backfill;
- no routine user-computer dependency;
- normal daily evidence maintenance does not require the user to run Git/BAT/PowerShell, ZIP transport or AI acceptance; the existing authoritative capture still retains its clean-code-identity integrity gate until M9.5 packages an equivalent verified release identity.

## Acceptance

See specs/m9-phase-4-background-evidence-calibration-observability.md.

## Ready-to-merge evidence

- PR #70 run #2549: Project OS, Source Coverage, Ruff 0/0, 965 Python / 0 warnings, Web build, 27 browser tests, Phase18, Phase21, M4 methodology frozen_match_37, Outcome Engine frozen_match_4.
- Formal release artifact: 10692084450 / sha256:891a269bc1fb643e4d016f0bfd46da74131e1325358f54660dacf65c41f0813d.
- Final merge still requires an exact ledger-bearing PR rerun and canonical-main post-merge validation.
