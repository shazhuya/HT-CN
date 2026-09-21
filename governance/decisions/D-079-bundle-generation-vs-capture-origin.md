# D-079 — Bundle-generation identity is distinct from immutable capture origin

status: active
date: 2026-09-21

## Decision

An M7 transport bundle may be generated on a canonical main commit newer than the commit that created its latest immutable authoritative capture.

- `code_head` remains a backward-compatible transport-generation identity.
- `bundle_generation_code_head` makes that meaning explicit.
- `latest_capture_code_head` records the immutable origin of the latest committed capture.
- A newer bundle-generation head does not rewrite or invalidate an older committed capture.

For same-trading-date reruns:

- same date + same capture transaction id + same capture count is an idempotent rerun;
- same date + different capture transaction id is a blocker;
- capture date/count regression is a blocker;
- if a previously accepted same-date outcome snapshot exists, an unexplained snapshot-id change is a blocker.

Acceptance remains read-only and never modifies authoritative evidence.

## Inference boundary

This decision changes transport/intake identity semantics only. It does not alter M4 methodology, Outcome Engine, Source semantics, harmonic geometry, lifecycle semantics, or ISSUE-0066. Statistical, alpha, win-rate and profitability inference remain prohibited.
