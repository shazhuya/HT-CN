# M7.5 — Evidence Acceptance and Idempotent Rerun Contract

status: planned

## 1. Identity model

The transport bundle has two different identities:

- bundle-generation identity: the clean canonical checkout used to package the ZIP;
- capture-origin identity: the immutable code head stored in the latest committed capture.

The exporter must expose both explicitly. Existing `code_head/worktree_clean` remain backward-compatible aliases for bundle generation.

## 2. Intake compatibility

For new bundles with explicit `latest_capture_code_head`, intake compares that field to the committed capture origin. A newer bundle-generation head becomes a warning, not a blocker.

For older bundles without explicit capture-origin identity, the historical strict `code_head == latest capture code_head` rule remains in force.

The latest committed capture itself must still have `worktree_clean=true`.

## 3. Read-only automated acceptance

`assess_m7_evidence_bundle` and its CLI must:

- reuse transport verification and authoritative intake recomputation;
- require M4 methodology freeze `37/37 frozen_match`;
- require Outcome Engine freeze `4/4 frozen_match`;
- require strict QFQ ready for every initialized instrument;
- require at least one valid committed future capture;
- never modify authoritative evidence;
- always keep statistical/alpha/win-rate/profitability/trade-instruction flags false.

## 4. Idempotency classification

Given an optional previous accepted receipt:

- newer date with monotonic capture-count growth => `new_capture`;
- same date + same transaction + same count => `idempotent_rerun`;
- same date + different transaction => `not_ready`;
- date/count regression => `not_ready`;
- previously accepted same-date outcome snapshot changing unexpectedly => `not_ready`.

## 5. Release gates

Require Project OS, Source Coverage, Ruff 0/0, full Python zero-warning suite, continuation bundle, Web, formal browser gates, Phase18, Phase21, methodology 37/37 and Outcome 4/4 before merge. No Private-M1 run is required to validate implementation.
