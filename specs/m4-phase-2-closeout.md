# M4 Phase 2 Closeout — Prospective Evidence Integrity

## Scope

This closeout freezes the evidence-integrity foundation required before HT-CN treats future
A-share lifecycle captures as a prospective research cohort.

It does **not** close M4 as a whole and does not authorize alpha / win-rate / return inference.

## Frozen baseline

- [x] M3 Source-Clock lifecycle is the product baseline.
- [x] Real T0 (2026-09-17) is frozen as baseline inventory.
- [x] T0 baseline rows are never prospective outcome observations.
- [x] Existing Source Terminal history inside T0 is not backdated into prospective evidence.
- [x] 5-0 remains production-quarantined.
- [x] Alternate Bat remains source-conflict fail-closed.
- [x] BSE remains deferred.

## Prospective chronology

- [x] Stable candidate keys use anchor trade dates rather than rolling-window indexes.
- [x] Candidate disappearance is not interpreted as invalidation.
- [x] Reappearing candidates preserve cohort identity.
- [x] Zero-candidate capture dates are explicit.
- [x] Historical backfill is rejected after transaction activation.
- [x] Same-date fact drift fails closed.
- [x] Provider-confirmed latest closed trade day is required.
- [x] Partial-universe diagnostic runs cannot create authoritative evidence.

## Atomic evidence

- [x] Future authoritative evidence is one immutable committed-capture transaction.
- [x] Transaction write uses temp + flush + fsync + atomic replace.
- [x] Frozen legacy baseline is separate from future committed captures.
- [x] Transaction filename / transaction-id / row-id tamper checks are enforced.
- [x] Full instrument coverage is required.
- [x] Compatibility journal / manifest are non-authoritative.
- [x] Missing or corrupt mirrors can be rebuilt from authoritative evidence without modifying it.

## Suspension correctness

- [x] Only positive full-day suspension evidence permits stale-bar continuity.
- [x] Intraday suspension does not qualify for full-day carry-forward.
- [x] Current-day bar plus full-day suspension evidence is a hard conflict.
- [x] Suspended capture rows contain no synthetic current-day OHLC/volume.
- [x] Suspended candidates remain scanner-present for continuity.
- [x] First observation on a suspended carry-forward day cannot enroll into the outcome cohort.
- [x] Previously enrolled candidates preserve cohort membership across confirmed suspension.

## Outcome enrollment boundary

- [x] `prospective_new` and `prospective_outcome_eligible` are separate facts.
- [x] Outcome enrollment requires a first post-T0 traded observation.
- [x] Candidate must still be forming and pre-terminal.
- [x] Source Raw PRZ must be resolved and valid.
- [x] Source Terminal must not already have occurred.
- [x] Source-fidelity-blocked patterns cannot enroll.
- [x] No return / MFE / MAE / win rate / alpha is computed in Phase 2.

## Methodology provenance — D-028

- [x] New authoritative captures use transaction schema v2.
- [x] Every v2 capture stores methodology contract version + deterministic SHA-256 fingerprint.
- [x] Methodology identity participates in the transaction ID.
- [x] Fingerprint coverage includes candidate identity, ratios, Source PRZ/lifecycle,
  RSI BAMM, Shark/5-0 source handling and prospective-enrollment code.
- [x] All fingerprint component paths exist in the current repository tree.
- [x] One active committed chain may contain only one methodology identity.
- [x] Current-code methodology mismatch is an evidence-health hard blocker.
- [x] Pre-fingerprint schema-v1 captures remain readable only for migration audit.
- [x] A schema-v1 chain cannot silently accept a schema-v2 append.
- [x] Compatibility manifest and mirror integrity expose/check methodology identity.
- [x] Transition and prospective-observation reports expose authoritative methodology identity.
- [x] Frozen T0 is not rewritten merely to attach a new fingerprint.

## Static integration audit

- [x] Production capture path passes methodology identity into `build_committed_capture`.
- [x] Modified research test fixtures pass methodology identity into committed-capture builders.
- [x] Methodology fingerprint component tree audit: 32 / 32 paths present.
- [x] Evidence-health reports structured blockers rather than mutating evidence.
- [x] Project context, decision log, session log and PR description are aligned to Phase 2.8.

## One-click private-M1 handoff

- [x] Local checkout preflight runs before any private M1 update or authoritative capture.
- [x] Preflight requires the frozen M4 branch, minimum safe checkpoint ancestry and a clean worktree.
- [x] Preflight failure guarantees that neither M1 update nor authoritative capture starts.
- [x] One-click local capture first runs full M1 smart daily update, then capture, health, transition, observation and transport-bundle stages.
- [x] M1 update failure skips new authoritative capture instead of accepting stale market data.
- [x] M1 update log is included in the transport bundle for diagnosis.
- [x] Final exit code is non-zero if any M1 / capture / health / report / bundle gate fails.
- [x] Transport bundle contains available frozen baseline, committed transactions and derived reports.
- [x] Bundle carries SHA-256 file records and current methodology provenance.
- [x] Bundle is explicitly non-authoritative and never modifies committed evidence.
- [x] Corrupt authoritative files are preserved in the bundle for diagnosis rather than silently repaired.

## External execution gates still open

- [ ] GitHub-hosted deterministic Python/Web job observed with real steps and logs.
  Current runner behavior still terminates before steps are allocated; this is infrastructure
  evidence absence, not a code-test pass and not a code-test failure.
- [ ] First real post-T0 fingerprinted future capture generated from the user's private M1
  dataset.
- [ ] At least one strict `prospective_outcome_eligible` candidate observed prospectively.
- [ ] Future outcome protocol separately preregistered before any performance inference.

## Closeout interpretation

Phase 2 evidence architecture is **structurally ready for the first fingerprinted future
capture**, subject to the open external execution gates above.

This statement means the provenance / chronology / no-lookahead evidence path is frozen
enough to begin collecting future evidence.

It does **not** mean HT-CN has demonstrated profitability, alpha, a win rate, expected return,
or a buy/sell edge.
