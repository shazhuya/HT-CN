# D-066 — Private-M1 closeout requires end-of-run main identity and one portable evidence bundle

status: active
change: CR-0066
date: 2026-09-19

## Decision

A private-M1 current-market closeout is accepted only when:

1. the final local HEAD still exactly matches remote `main` after the entire run;
2. all Phase23/Phase19/Phase21 identities converge on the same trade date and delivery identity;
3. evidence is captured into one independently hash-verified portable ZIP;
4. hosted CI validates the mechanism but can never substitute for the real private-M1 run.

The final evidence bundle is operational QA evidence and is not M4 authoritative research evidence.

## Rationale

The existing preflight verifies main freshness before mutation, but a long real closeout can become stale if main moves while it is running. The end-of-run remote-main check closes that race. A single portable evidence ZIP also eliminates multi-file/manual screenshot handoff ambiguity.
