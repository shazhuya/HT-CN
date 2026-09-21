# M9.0 — Product Completion Policy & Roadmap

status: implementing

## 1. Permanent track separation

Development mainline: M9.
Background evidence: M7.
Claims/calibration: M8.

M7 and M8 are not prerequisites for starting or finishing non-statistical M9 product work. ISSUE-0066 remains binding for win-rate/alpha/profitability/statistical claims.

## 2. Stable Product target

Stable Product means normal user operation can update data, run harmonic analysis, render the interactive workbench, maintain evidence and recover from ordinary faults without daily command-line/ZIP/AI supervision.

It does not mean that every long-horizon research metric is already statistically available.

## 3. M9 roadmap

### M9.1 Automated Market Data & Scheduling Service
Automate market calendar, incremental data, QFQ, provider failover/retry and health. Remove daily BAT/PowerShell from normal operation.

### M9.2 Automated Harmonic Analysis Runtime
Automate data-driven incremental analysis while preserving Source truth and no-future-node rules.

### M9.3 End-to-End Product Workbench
Integrate symbol selection, chart, harmonic geometry, PRZ, lifecycle, key levels and Chinese explanations.

### M9.4 Background Evidence / Calibration Boundary & Observability
Run M7 evidence/outcomes in the background; keep M8 unavailable until empirical gates are met; surface insufficient-evidence state explicitly.

### M9.5 Reliability, Packaging & Zero-CLI Operation
Productize startup, upgrade, migration, backup/recovery, diagnostics and daily operation.

### M9.6 Stable Product Release Acceptance
End-to-end acceptance, formal release artifacts, documentation and stable version.

## 4. User-computer rule

User computer is exceptional. It may be requested only when private/local state is materially required and no hosted/fixture/agent-controlled substitute exists. Daily evidence collection is explicitly not a valid reason.

## 5. Project OS enforcement

The machine-readable policy must be a required canonical file, included in the continuation bundle and represented in the Resume Pack. Validation must fail when:

- product mainline is not M9;
- ISSUE-0066 is configured to block product release;
- daily manual Private-M1 is required;
- stable release requires ISSUE-0066 closure;
- M7 is not represented as non-blocking background evidence;
- M8 is represented as a product-release blocker.

## 6. Exit gate

- policy/Blueprint/Decision/Issue/State/Milestones agree;
- AGENTS and CHAT_CONTINUATION teach the same boundary;
- continuation bundle contains the policy;
- Project OS tests enforce it;
- M9.1-M9.6 are explicit;
- all hosted and release/freeze gates remain green.
