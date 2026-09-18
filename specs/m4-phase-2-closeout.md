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

- [x] Current authoritative captures use transaction schema v4; schema v2/v3 are historical pre-T1 provenance.
- [x] Every fingerprinted capture stores methodology contract version + deterministic SHA-256 fingerprint.
- [x] Methodology identity participates in the transaction ID.
- [x] Fingerprint coverage includes candidate identity, ratios, Source PRZ/lifecycle,
  RSI BAMM, Shark/5-0 source handling and prospective-enrollment code.
- [x] All fingerprint component paths exist in the current repository tree.
- [x] One active committed chain may contain only one methodology identity.
- [x] Current-code methodology mismatch is an evidence-health hard blocker.
- [x] Pre-fingerprint schema-v1 captures remain readable only for migration audit.
- [x] Older schema chains cannot silently accept a schema-v3 append; mixed transaction schemas fail closed.
- [x] Compatibility manifest and mirror integrity expose/check methodology identity.
- [x] Transition and prospective-observation reports expose authoritative methodology identity.
- [x] Frozen T0 is not rewritten merely to attach a new fingerprint.

## Static integration audit

- [x] Production capture path passes methodology identity into `build_committed_capture`.
- [x] Modified research test fixtures pass methodology identity into committed-capture builders.
- [x] Methodology v3 fingerprint component tree audit: 37 / 37 paths present.
- [x] Evidence-health reports structured blockers rather than mutating evidence.
- [x] Project context, decision log, session log and PR description are aligned to Phase 2.8.

## Outcome cohort follow-up — D-032

- [x] Schema v3 stores scanner-present journal rows separately from scanner-absent cohort follow-up rows.
- [x] Follow-up coverage equals prior outcome-enrolled cohort minus current scanner-present candidates.
- [x] Missing or extra follow-up rows fail closed.
- [x] Traded follow-up preserves current-day OHLC/volume without creating lifecycle state.
- [x] Full-day suspension follow-up preserves event provenance without synthetic OHLC.
- [x] Prospective observation reports consume follow-up market facts while scanner presence remains absent.
- [x] Methodology contract v2 fingerprints 37 files, including capture chronology, enrollment normalization and follow-up semantics.
- [x] No post-T0 fingerprinted future capture existed before methodology-v2 freeze.

## Price-basis provenance — D-034

- [x] Formal prospective evidence accepts only QFQ / QFQ carry-forward.
- [x] Raw fallback is excluded from validation enrollment and authoritative capture.
- [x] Formal rows persist `price_mode` and deterministic `price_basis_id`.
- [x] QFQ basis ID ignores same-factor carry-forward dates but changes with factor-regime changes.
- [x] Committed capture schema v4 requires basis provenance on journal and follow-up rows.
- [x] Prospective observation schema v3 freezes enrollment basis and reports later drift.
- [x] Basis drift is surfaced but never auto-rebased in Phase 2.
- [x] Methodology contract advanced to v3 with the same 37 component paths.
- [x] Exact methodology-v3 freeze commit is `2b0aa92d292410098d9678a3bfd3102f3df1ed4b`.
- [x] No post-T0 future committed capture existed before the v3 freeze.

## Exact pre-T1 methodology code freeze — D-033

- [x] Historical methodology-v2 freeze was `084ddf...`; current T1 freeze is methodology-v3 commit `2b0aa92d292410098d9678a3bfd3102f3df1ed4b`.
- [x] Current contract version / component count are fixed at v3 / 37.
- [x] Capture preflight rejects any post-freeze change to the 37 methodology paths.
- [x] Methodology guard runs before M1 update or authoritative capture.
- [x] Guard provenance report is included in the evidence transport bundle.
- [x] Audit from frozen commit to current closeout found 0 methodology-component changes.

## One-click private-M1 handoff


- [x] Local checkout preflight runs before any private M1 update or authoritative capture.
- [x] Preflight requires the frozen M4 branch, minimum safe checkpoint ancestry and a clean worktree.
- [x] Preflight failure guarantees that neither M1 update nor authoritative capture starts.
- [x] One-click local capture first runs full M1 smart daily update, then capture, health, transition, observation and transport-bundle stages.
- [x] M1 update failure skips new authoritative capture instead of accepting stale market data.
- [x] M1 update log is included in the transport bundle for diagnosis.
- [x] Final exit code is non-zero if any M1 / capture / health / report / bundle gate fails.
- [x] Transport bundle contains available frozen baseline, committed transactions and derived reports.
- [x] Transport ZIP is verified before atomic publication and verified again after publish.
- [x] Manifest member size/SHA, duplicate/extra member and unsafe-path checks fail closed.
- [x] Evidence-health-blocked bundles remain transport-valid diagnostics and never masquerade as evidence ready.
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
