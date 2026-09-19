# M6 Phase 2 — Real Private-M1 Closeout / Identity-Bound Evidence Bundle v1

status: implementing
change: CR-0066
decision: D-066

## 1. Objective

M6.2 closes the empirical gap left intentionally open by M5 Phase21/23:

> run the current formal `main` against the user's real private M1 market database, then prove that the resulting preflight, daily-close pipeline, Phase19 delivery, structural closeout, Chromium audit and final closeout all belong to the same Git HEAD / trade date / delivery identity.

Hosted CI MUST NOT claim that this private-M1 run happened.

## 2. Reuse, do not rewrite

M6.2 reuses the frozen chain:

1. Phase23 read-only preflight;
2. Phase9 daily close;
3. Phase19 portable delivery;
4. Phase21 structural closeout;
5. Phase21 real browser source;
6. dynamic Chromium audit;
7. independent browser verification;
8. Phase21 final closeout.

M6.2 adds a second independent identity audit and a portable evidence bundle. It does not replace any M5 verifier.

## 3. Single user action

Recommended local entrypoint:

`运行HT-CN M6.2真实Private-M1最终收口.bat`

It MUST:

1. validate Project OS current state;
2. call the existing frozen M5 real-closeout BAT;
3. after M5 reports `full_closeout_ready=true`, run the M6.2 independent verifier;
4. build and re-verify one ZIP;
5. print exactly one upload artifact path.

No dependency installation, Git pull/fetch/reset, market-data repair, or browser installation is allowed in this entrypoint.

## 4. End-of-run remote-main recheck

Phase23 checks remote main before mutation. M6.2 MUST re-check `git ls-remote origin refs/heads/main` after the long real closeout.

Hard blocker:

`remote_main_head != local HEAD`

This prevents a closeout that started on current main but became stale while it was running from being labeled current-main ready.

No automatic repair is allowed.

## 5. Project OS binding

The real run is valid only when:

- current branch = `main`;
- worktree is clean;
- Project OS validates;
- `PROJECT_STATE.current.phase == M6.2`;
- `PROJECT_STATE.current.active_change == CR-0066`;
- current status explicitly allows a private run;
- the current Git HEAD is the exact remote main HEAD at M6 finalization time.

## 6. Required identity chain

The following must agree:

### Git
- preflight HEAD;
- structural `current_head`;
- final `main_head`;
- local HEAD;
- remote main HEAD at finalization.

### Trade date
- Phase19 latest pointer;
- immutable archive manifest;
- structural closeout;
- browser source;
- browser verification;
- final closeout.

### Portable bundle identity
- Phase19 pointer `bundle_sha256`;
- actual portable delivery SHA-256;
- immutable archive manifest;
- structural `bundle_sha256`;
- browser source `source_identity`;
- browser verification `source_identity`;
- final `bundle_sha256`.

### Input identity
- Phase19 pointer `input_identity_fingerprint`;
- immutable archive manifest `input_identity_fingerprint`.

### Pipeline identity
- Phase19 pointer `pipeline_report_sha256`;
- actual pipeline report SHA-256;
- immutable archive manifest `pipeline_report_sha256`.

### Browser source identity
- browser-source report workspace/inspection hashes;
- actual Phase19 workspace / inspector files;
- browser evidence screenshot file hashes;
- independent browser verification status = valid.

Any mismatch is a blocker.

## 7. Evidence bundle

Output:

`artifacts/reports/htcn-m6-private-m1-closeout-evidence.zip`

The bundle includes, at minimum:

- M6.2 verification report;
- Project State snapshot;
- Phase23 preflight;
- daily close pipeline report;
- Phase19 run report;
- Phase19 latest pointer;
- Phase21 structural report;
- Phase21 browser source;
- Phase21 raw browser evidence;
- Phase21 browser verification;
- Phase21 final report;
- immutable Phase19 archive manifest;
- immutable Phase19 delivery/v4/inspector/workspace files;
- all screenshot evidence referenced by the browser report;
- SHA-256 manifest for every bundled member.

The bundle itself is independently re-opened and verified after write.

## 8. Authority boundary

The M6 evidence bundle is operational acceptance evidence, NOT M4 authoritative research evidence.

It MUST NOT:

- mutate harmonic identity;
- mutate Source Raw PRZ;
- mutate Source lifecycle;
- write or alter M4 evidence;
- create review/follow-up events;
- infer win rate / alpha / profitability;
- rank outcomes;
- execute trades.

## 9. Status

Core M6.2 result:

- `ready`
- `ready_with_warnings`
- `invalid`

`full_closeout_ready=true` is allowed only when every hard identity check passes.

Warnings from Phase23 / Phase21 may be carried forward but cannot hide any M6 hard mismatch.

## 10. Hosted acceptance

Hosted CI validates:

- verifier logic;
- remote-main drift failure;
- Project OS phase/change failure;
- trade-date mismatch failure;
- bundle identity mismatch failure;
- pipeline hash mismatch failure;
- archive member tamper failure;
- browser source hash mismatch failure;
- evidence bundle manifest/hash verification;
- bundle tamper detection;
- zero-candidate-day compatibility;
- BAT ordering;
- no auto-install/update commands;
- no M2/M3/M4/M5 semantic mutation.

Hosted CI MUST state that no real private-M1 current-market run occurred.

## 11. M6.2 completion boundary

Engineering may be merged to main before the user's private M1 run.

After merge, M6.2 state becomes:

`awaiting_private_run`

M6.2 is NOT closed until a real local evidence ZIP produced by the current main is independently inspected and accepted.

Only after that evidence is accepted may:

- ISSUE-0061 close;
- `private_m1.current_market_full_closeout_ready` become true;
- CR-0066 close;
- M6.2 close;
- M6.3 become next active task.

## 12. Evidence bundle tamper-hardening

The standalone ZIP verifier MUST remain valid even when the uploaded artifact is inspected outside the original private-M1 machine. Therefore it rejects more than simple byte/hash mismatches:

- archive member names must be safe relative POSIX paths;
- every archive payload member must be listed in the manifest and no extra member is accepted;
- browser evidence trade date/source identity must match the M6 manifest;
- screenshot size/hash records must match the actual bundled screenshots;
- browser source workspace, inspector and structural hashes must match bundled members;
- immutable Phase19 archive member hashes must match the corresponding bundled members.

This prevents a re-packed ZIP from becoming valid merely because an attacker recomputed the outer manifest hashes after altering inner semantic evidence.
