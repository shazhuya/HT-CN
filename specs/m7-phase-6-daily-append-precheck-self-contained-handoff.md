# M7.6 — Daily Append Precheck and Self-Contained Handoff

status: planned

## 1. Operator states

After M1:

- `capture_due`: exactly one new closed session; run strict QFQ, capture and outcome.
- `idempotent_noop`: latest closed session already has the latest committed capture; skip append-only work and continue read-only health/transition/observation/status/bundle/acceptance.
- `blocked`: missed sessions, clock regression or evidence/calendar contradiction.

## 2. No-backfill boundary

M7 prospective evidence is daily and forward-only. If more than one closed trading session exists after the latest committed capture, the wrapper must stop rather than silently capture only the newest day.

## 3. Self-contained transport

The wrapper must generate `m7-accumulation-status.json` before `m4-evidence-bundle.zip`. The bundle must include:

- `reports/m7-append-precheck.json`;
- `reports/m7-accumulation-status.json`;
- `reports/m7-accumulation-status.md`.

The manifest must expose append action, latest closed date, pending count, M7 accumulation status and ISSUE gate.

## 4. Acceptance rule

Strict current-run QFQ remains mandatory for `capture_due`. For `idempotent_noop`, a missing QFQ report is allowed only if transported precheck facts prove:

- precheck status=ready;
- latest closed date == latest committed capture date;
- pending closed trade count=0.

Any inconsistency remains not-ready.

## 5. Frozen boundaries

No frozen M4/Outcome/Source/lifecycle component changes. Statistical, alpha, win-rate, profitability and trade-instruction flags stay false under ISSUE-0066.

## 6. Release gates

Project OS, Source Coverage, Ruff 0/0, full Python zero-warning suite, continuation bundle, Web build, 25 browser tests, Phase18, Phase21, methodology 37/37 and Outcome 4/4 must pass before merge.
