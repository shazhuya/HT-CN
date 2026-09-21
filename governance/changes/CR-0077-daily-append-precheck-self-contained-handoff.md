# CR-0077 — M7.6 Daily Append Precheck and Self-Contained Handoff

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 2ce240a2acb8032c3a4d06951279064acfd2cc18
target: main
milestone: M7.6

## Trigger

M7.5 solved read-only acceptance and same-transaction idempotency after a bundle already exists. The daily operator still attempts QFQ/capture/outcome on a session that has already been committed, and it exports the transport ZIP before generating M7 accumulation status.

## Objective

1. Decide append/no-op/block immediately after M1 updates the closed-session clock.
2. Avoid all append-only work on same-day reruns.
3. Fail closed when one or more required daily captures were skipped beyond the single current session.
4. Generate M7 status before packaging.
5. Carry precheck and M7 status inside the one uploaded ZIP.
6. Keep M7.5 acceptance strict for real new captures while permitting no-QFQ only for cryptographically transported, verified no-op prechecks.

## Non-goals

No backfill, no trading logic, no methodology changes, no inference changes, no automatic mutation of accepted evidence.

## Acceptance

See `specs/m7-phase-6-daily-append-precheck-self-contained-handoff.md`.
