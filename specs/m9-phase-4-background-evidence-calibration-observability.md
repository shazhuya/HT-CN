# M9.4 — Background Evidence, Calibration Boundary & Observability

status: implementing

## 1. Objective

Move M7 from a user-invoked evidence workflow into product infrastructure while keeping evidence semantics immutable and M8 inference disabled until genuinely authorized.

## 2. Background evidence cycle

The product service may orchestrate only established primitives:

1. verify M4 methodology freeze;
2. verify Outcome Engine freeze;
3. evaluate M7 append precheck against the latest canonical closed session;
4. on capture_due only, run strict formal-QFQ readiness and the existing authoritative lifecycle capture;
5. always rebuild evidence-chain health, lifecycle transitions, prospective observations and M7 accumulation status;
6. on a newly accepted capture only, run the existing preregistered Outcome v2 step;
7. persist one atomic service status and advance the success watermark only when required authoritative steps pass.

The service must not reimplement capture, outcome or lifecycle semantics.

## 3. No-op and retry semantics

- idempotent_noop is a successful cycle and must not rerun append-only QFQ/capture/outcome work;
- an operational failure keeps the previous success watermark unchanged and is retryable;
- multiple missed closed sessions remain fail-closed because M7 historical backfill is forbidden;
- transport ZIP/export/acceptance are not part of normal background product operation.

## 4. Operational fault vs evidence insufficiency

The status contract must expose these separately:

- operational_state: healthy / degraded / blocked;
- operational_fault: true only for execution/data/integrity failure;
- evidence_state: accumulating / insufficient_evidence / blocked;
- evidence_insufficient: true when the chain is healthy but ISSUE-0066/M8 authorization is not satisfied;
- calibration_state: disabled_insufficient_evidence / disabled_operational_fault / authorized.

A healthy service with insufficient empirical evidence is not a product fault.

## 5. M8 fail-closed authorization

M8 is authorized only when all are true:

- ISSUE-0066 is no longer open;
- evidence-chain health has no blockers;
- M7 accumulation status is readable and not blocked;
- an explicit machine-readable M8 calibration authorization exists and is marked authorized.

No implicit sample-size threshold is invented in M9.4. Until a later evidence decision creates that authorization, product UI/API must say evidence is insufficient and statistical features are unavailable.

## 6. Scheduling and upstream coordination

The background evidence service follows the latest closed canonical trade date after automated market-data readiness. It must be idempotent and safe to poll. Normal daily operation must require no BAT/PowerShell or user command line. The frozen authoritative capture keeps its existing clean code-identity gate; M9.4 does not bypass that evidence-integrity rule. M9.5 packaging must provide an equivalent verified release identity so packaged zero-CLI operation does not depend on an interactive Git worktree.

## 7. Product observability

Expose a read-only API status and product card showing:

- service health;
- latest evaluated/committed capture date;
- append decision;
- evidence-chain blockers/warnings;
- prospective candidate and outcome-snapshot counts when available;
- M8 calibration state;
- concise Chinese diagnostics explaining whether action is blocked by a product fault or simply by insufficient evidence.

## 8. Tests

Deterministic tests must cover:

- first/new-session due cycle;
- same-session idempotent no-op;
- capture failure does not advance watermark;
- evidence health blocker becomes operational blocked;
- healthy chain plus ISSUE-0066 open becomes insufficient_evidence, not operational fault;
- explicit future authorization contract is required before calibration can become authorized;
- atomic status read/write and unreadable-state diagnostics;
- API/product rendering does not fabricate win-rate/alpha/profitability values.

## 9. Exit gate

M9.4 may close only when:

- M7 capture/outcome/health/cohort maintenance is productized as background infrastructure;
- normal daily operation no longer needs the user to run the M7 BAT or exchange ZIP evidence;
- M8 remains fail-closed under ISSUE-0066;
- the product visibly distinguishes operational faults from evidence insufficiency;
- all hosted Python/Web/browser/freeze gates remain green;
- no user-computer validation is required;\n- M9.5 has an explicit release-identity exit gate so zero-CLI packaging preserves the M4 clean-code provenance guarantee without requiring Git worktree management.
