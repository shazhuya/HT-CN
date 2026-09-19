# CR-0066 — M6.2 Real Private-M1 Closeout

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
target: main
milestone: M6.2

## Objective

Complete all engineering needed for one-action real private-M1 current-market closeout and portable identity-bound evidence collection.

## Must solve

1. reuse M5 Phase21/23 rather than duplicating it;
2. re-check remote main at the END of the real run;
3. independently bind Git HEAD / trade date / Phase19 bundle / input identity / pipeline hash / browser evidence;
4. generate one self-verifying ZIP;
5. make local user action one BAT;
6. make hosted CI prove mechanism only, never private-M1 completion;
7. keep M6.2 open after merge until real private evidence is inspected.

## Acceptance

- M6.2 spec exists;
- D-066 is active;
- Project State enters M6.2 implementing;
- independent verifier implemented;
- evidence bundle builder/verifier implemented;
- one-action BAT implemented;
- unit/regression tests cover identity drift and tamper;
- branch CI green;
- PR->main formal release green;
- merge-main push green;
- post-merge state becomes awaiting_private_run;
- real private-M1 evidence remains the only remaining empirical gate.

## Non-goals

No harmonic ratios, identity, PRZ, lifecycle, M4 methodology/outcome engine, M5 product semantics, win-rate/alpha claims, or trade execution changes.

## Hosted implementation validation

- Project OS drift failure #2061 / `35437436500` preserved as A-20260919-0066-002;
- corrected without weakening fail-closed validation;
- final branch run #2072 / `35437669271`: success;
- Project OS integrity: success;
- Python: **866 passed / 1163 warnings**;
- Web build: success;
- M6.2 tests cover end-of-run remote-main drift, state mismatch, trade-date mismatch, archive tamper, screenshot tamper, portable bundle identity, rehashed semantic tamper, bundle self-verification and one-action BAT boundaries;
- no M2/M3/M4/M5 semantic file modified.

Formal PR->main release validation remains required before merge.

## Final pre-merge gate

- lifecycle-state regression #2076 / `35437727008` preserved as A-20260919-0066-004;
- fix keeps phase=`M6.2` and active change=`CR-0066` strict while allowing only explicit lifecycle progression states;
- final PR run #2080 / `35437784106`: success;
- formal Project OS integrity: success;
- formal main lineage: success;
- existing browser acceptance: **24 passed**;
- Phase18: **1 passed**;
- Phase21: **1 passed**;
- M4 methodology: **frozen_match / 37 components**;
- Outcome Engine: **frozen_match / 4 components**;
- formal release artifact ID: **10582497478**.

CR-0066 engineering is ready to merge. The empirical private-M1 run remains intentionally pending until after formal main integration.

## Latest frozen-head validation

- final engineering HEAD before merge: `4a87dcaa967b573ef80691f99e9fa57a38f5aaab`;
- PR run #2086 / `35437936795`: success;
- Project OS integrity: success;
- deterministic tests: success;
- Web build: success;
- formal main release integrity: success;
- existing browser acceptance: **24 passed**;
- Phase18: **valid**;
- Phase21: **valid**;
- M4 methodology: **frozen_match / 37 components**;
- Outcome Engine: **frozen_match / 4 components**.

This supersedes the earlier #2080 validation pointer. No implementation changes occurred after this validation.

## Evidence-bundle hardening audit

Independent pre-merge review found that ordinary manifest hash verification could be stricter against a malicious re-packed ZIP whose outer hashes were recomputed. The verifier was hardened without changing any market/research semantics:

- reject unsafe archive paths;
- reject unlisted/extra archive members;
- independently re-bind browser evidence trade date and source identity;
- bind every screenshot record to the actual bundled screenshot bytes;
- bind browser-source workspace / inspector / structural hashes to bundled members;
- bind immutable Phase19 archive member hashes to bundled members;
- add regression tests for unlisted unsafe members, rehashed browser-evidence semantic tamper, and rehashed workspace tamper.

After this implementation change, prior ready-to-merge validation is historical only. A new frozen-head validation is required.

## Hardened final validation

- hardened implementation HEAD: `0eed2c90ca3b75c98345155766df6c4f387f28bb`;
- final PR validation #2101 / `35441597214`: success;
- Python: **869 passed / 1163 warnings**;
- Web build: success;
- existing browser acceptance: **24 passed**;
- Phase18: **1 passed / valid**;
- Phase21: **1 passed / valid**;
- M4 methodology: **frozen_match / 37 components**;
- Outcome Engine: **frozen_match / 4 components**;
- formal release artifact ID: **10583747910**;
- diff audit: no M2/M3/M4/M5 frozen implementation file modified.

The hardened verifier implementation is ready to merge. Real private-M1 execution remains intentionally pending until the code is integrated into formal main.

## Integrated engineering release / awaiting private run

- PR #39 merged with merge commit `86fd17d01b3b9c2fc597d500723c6966c9a2250f`;
- merge-generated main push #2108 / `35443729796`: success;
- Python: **869 passed / 1163 warnings**;
- Project OS integrity: success;
- formal main release integrity: success;
- existing browser acceptance: **24 passed**;
- Phase18: **1 passed / valid**;
- Phase21: **1 passed / valid**;
- M4 methodology: **frozen_match / 37 components**;
- Outcome Engine: **frozen_match / 4 components**;
- formal release artifact ID: **10584915975**.

Engineering and repository integration are complete.

CR-0066 intentionally remains open as `postmerge_pending` until the empirical private-M1 run is performed on the machine that owns the local M1 database.

The only remaining user action is:

`运行HT-CN M6.2真实Private-M1最终收口.bat`

On success it produces exactly one upload artifact:

`artifacts/reports/htcn-m6-private-m1-closeout-evidence.zip`

Raw M1 catalog/Parquet/daily-delta data should not be uploaded. M6.2 closes only after the ZIP is independently verified and accepted.

## Post-merge Project OS cleanup

Final audit after PR #40 found one non-functional duplicate declaration of `ALLOWED_CHANGE_STATUS` in `scripts/project_state.py`.

It was removed and a regression assertion was added requiring exactly one lifecycle-status declaration.

This cleanup:

- does not alter M6.2 acceptance semantics;
- does not alter private-M1 requirements;
- does not alter M2/M3/M4/M5 implementation;
- keeps M6.2 in `awaiting_private_run`;
- is recorded as A-20260919-0066-010.

## Final cleanup lifecycle closure

The cleanup lifecycle is now completely preserved instead of stopping at the first local success:

- A-20260919-0066-011: failed, workflow `35444796422`, literal `\\n` caused pytest collection `SyntaxError`;
- A-20260919-0066-012: failed, workflow `35444858864`, first repair did not actually replace the literal escape;
- the exact source was repaired and verified before the final merge;
- PR #41 merged as `cffe3956f4a053581a512a3df24413f400ab3be5`;
- push-main workflow `35445071382` / run #2133 completed successfully;
- deterministic tests and formal-main-release-integrity both succeeded;
- the verified final success is recorded as A-20260919-0066-013.

`86fd17d01b3b9c2fc597d500723c6966c9a2250f` remains the latest integrated M6.2 product release. `cffe3956f4a053581a512a3df24413f400ab3be5` is the latest successful governance validation. This distinction is explicit and M6.2 remains `awaiting_private_run`.

## Stage-audit continuity and quality hardening

The 2026-09-19 stage audit found that the prior Project OS checks could still pass while the active spec status or final attempt pointer lagged behind Git/CI. This bounded hardening closes that gap without changing M1–M5 product or research semantics:

- `PROJECT_STATE.current.active_spec` must resolve through `required_specs` and its status must equal the current machine state;
- Change lifecycle status must be compatible with the current machine state;
- `PROJECT_STATE.current.latest_attempt_id` must resolve to one unique attempt belonging to the active CR;
- a successful latest attempt must bind the same commit and workflow run as `latest_validation`;
- attempt IDs are unique and the referenced attempt commit must be an ancestor of the current checkout;
- M6.2 spec now correctly states `awaiting_private_run`;
- the final PR #41 / push-main success is recorded as A-20260919-0066-013;
- Python dependency resolution is locked through `uv.lock` and `requirements-dev.lock`;
- the 1163-warning and repository-wide Ruff debt baselines are fail-on-growth CI gates;
- README now exposes current state, operator entrypoints, authority order, data boundaries and Source support limits.

The warning/lint budgets are containment gates, not debt closure claims. Existing debt remains tracked for bounded reduction. The real private-M1 run remains the only M6.2 empirical blocker.

Clean local validation on `ff644f45f048bc38d2c55ce10aaac8db719d6195` passed 872 Python tests with the warning budget unchanged at 1163. Ruff debt was 485, all newly added/materially edited Project OS files were clean, both M4 freeze guards matched, and the dependency lock validated. This is recorded as A-20260919-0066-015. Hosted branch validation remains required before merge.

The warning audit then eliminated the historical warning debt instead of merely containing it: 1160 repeated Pandas test deprecations were corrected with explicit day units, the deliberate duplicate-member ZIP tamper test now asserts its warning, and two locked upstream import deprecations are filtered by exact message. The pytest warning budget is now zero.

The first branch push attempt from `125872ed64415c09b6606dade08d091ef7413a7c` was blocked because the execution environment had no GitHub credential helper, token or authenticated GitHub CLI. No remote ref was created. This external-auth failure is preserved as A-20260919-0066-016 and is not represented as a code or CI failure.

The first zero-warning full run passed all 872 tests but correctly failed the new quality gate on one remaining `StarletteDeprecationWarning`. Its class inherits from `UserWarning`, not `DeprecationWarning`; the narrow exact-message filter was corrected to the real Starlette category without relaxing the zero budget. This failed attempt is preserved as A-20260919-0066-017.

The corrected clean run on `8f0b7ddcb42ba796766232bfcf3010a7ada3c6cd` passed 872 Python tests with zero warnings, Ruff debt 483, Project OS, both M4 freeze guards and the dependency lock. This is preserved as A-20260919-0066-018.

The final local release candidate `482a005e498e7b63ea57015074f9c689a56a0367` additionally passed the Web production build with the same 872/0 Python result, Ruff 483 budget, Project OS, both freeze guards and dependency lock. This is preserved as A-20260919-0066-019. The branch is frozen locally pending authenticated push and formal hosted validation.

The connected GitHub integration then published the six local commits as an equivalent hosted commit chain. GitHub API commit creation preserved every file tree and commit boundary but produced new commit-object SHAs. The first hosted run #2135 / `35448689280` therefore failed closed at Project OS because A-019 still named local-only commit `482a005e498e7b63ea57015074f9c689a56a0367`. This expected continuity failure is preserved as A-20260919-0066-020. The zero-warning baseline is rebound to remote-equivalent commit `8848d859b712ece8416abcaf2c26ecba74426ad1`, whose tree is identical to the validated local A-019 state; ancestry checks remain strict and a new hosted run is required.

The corrected hosted PR run #2137 / `35448896046` succeeded on remote head `4b664bd947565742577201f9be5af48539c386b2`: Project OS ready, 872 Python tests / 0 warnings, Ruff 483, Web production build, 24 deterministic browser tests, Phase18 and Phase21 acceptance, M4 methodology frozen-match (37), Outcome Engine frozen-match (4), and formal release artifact `10586213144`. This is preserved as A-20260919-0066-021. PR #42 is formally green and ready for review/merge; M6.2 remains `awaiting_private_run`.

The evidence-sync head `0d0c045df6ec41bdaffab04528a9a21590751503` then passed the final PR run #2139 / `35449160235` and was squash-merged through PR #42 as main commit `38ce7b45a67de66d2654c135c4b2691b736749ef`. Its file tree is identical to the validated PR head. The first main push #2140 / `35449318110` failed closed because the squash merge does not retain PR-branch commits as ancestors while `latest_attempt_id` still named one. This governance-continuity failure is preserved as A-20260919-0066-022; ancestry enforcement remains strict and a bounded main-line evidence sync is required.

The bounded main-line governance sync `e6dfccf18e52b10eb1e4520bcf60bc1d62430e41` then passed push workflow #2141 / `35449508107`: Project OS ready, 872 Python tests / 0 warnings, Ruff 483, Web production build, 24 deterministic browser tests, Phase18 and Phase21 acceptance, both M4 freeze guards, and formal artifact `10585884027`. This is preserved as A-20260919-0066-023. Quality hardening is integrated and main is green; M6.2 still awaits only the real private-M1 evidence ZIP and independent acceptance.

## Private-M1 BSE default-scope correction

The first real private-M1 run after the portable-continuity repair reached the M5 operator-cache finalization step and correctly failed closed because the initialized local universe contained `BSE.920001` at trade date `2026-09-15` while the active SSE/SZSE data were current through `2026-09-18`. All 56 instruments analyzed successfully; the blocker was mixed-as-of cache identity, not an instrument-analysis failure.

Project State already freezes `bse_default_scope` as `deferred`. The bounded correction therefore excludes `BSE.*` from the default M5/M6.2 operator universe while preserving any local BSE files untouched. Generic instrument discovery remains capable of returning BSE when no exchange filter is requested.

This correction does not alter harmonic identity, Source Raw PRZ, Source lifecycle, M4 evidence, Outcome Engine, or trading semantics. A fresh hosted validation and a fresh real private-M1 run on the resulting current main are required.

## Private-M1 Phase21 forming-Shark audit correction

The real private-M1 run on the post-BSE-scope main progressed through the dynamic Chromium audit and exposed a browser-test contract bug for a live forming Shark candidate. The transported visual semantics correctly reported schema `0XABC` with observed prefix ending at `B` and future `C` still missing, but the Phase21 Playwright test incorrectly treated `topology.observed_labels` as if it were the complete schema label set and unconditionally required the observed last label to be `C`.

This is a test/audit defect, not a harmonic-identity defect. Existing source-aligned visual semantics already define Shark as expected topology `0-X-A-B-C`, permit `forming_prefix` observations such as `0-X-A-B`, require missing future labels to remain undrawn, and prohibit fabrication of `D`.

The bounded correction makes Phase21 compare rendered nodes with `observed_labels`, separately verifies the canonical `expected_labels == [0,X,A,B,C]`, requires completed Shark to end at `C`, and requires forming Shark prefixes to report `C` among missing future labels. No product geometry, Source Raw PRZ, lifecycle, M4 evidence, or harmonic identity is changed.

A fresh hosted validation and a fresh private-M1 closeout on the resulting current main are required.

## Forming-Shark audit validation closeout

- real Private-M1 failure on main `8f38a628b068417164fd1caad01110d35c4b88b1` is preserved as A-20260919-0066-027;
- first hosted regression run #2177 / `35455483180` is preserved as A-20260919-0066-028; the forming-Shark browser case passed, while the stale five-screenshot Phase18 evidence contract failed closed;
- corrected hosted run #2179 / `35455632325` on `01e417129b8f48a287872737802d44b5917519c3` passed 880 Python tests / 0 warnings, Ruff 483, Web build, 24 existing browser tests, six-case Phase18 browser acceptance, Phase18 evidence verification (11 checks / 6 screenshots), Phase21 dynamic Chromium audit, Phase21 evidence verification, M4 methodology frozen-match (37), and Outcome Engine frozen-match (4);
- formal release artifact: `10588047315`.

This validates the audit correction without changing harmonic identity, Source Raw PRZ, Source lifecycle, M4 methodology, Outcome Engine or trade semantics. M6.2 remains `awaiting_private_run`; a fresh real Private-M1 run on the resulting canonical main is still required before any closeout claim.

## Dynamic Attempt-pointer continuity-test repair

Final ledger-bearing PR run #2183 / `35455810195` failed after Project OS and Ruff succeeded because two tests still asserted the historical literal attempt `A-20260919-0066-023`. The machine state had correctly advanced to A-20260919-0066-029.

The repair removes those stale numeric pins. Tests now validate the actual contract: state pointers resolve in the Attempt Ledger, belong to CR-0066, the hosted pointer is successful, and its workflow matches `latest_validation`. Runtime Project OS validation remains unchanged and fail-closed.

The failed candidate is A-20260919-0066-030; the bounded test repair is A-20260919-0066-031. A fresh complete PR validation is required before merge.

## Real Private-M1 empirical acceptance / closure

The final real Private-M1 run on canonical main `e40eb32253a03d62ce2c7bdd253762f824a54a26` produced the required portable evidence ZIP and it was independently accepted.

Acceptance identity:

- evidence ZIP SHA-256: `8a9146a503173b9f30de13792069d71d87c1ca1cae368c0d3773510933413b68`;
- trade date: `2026-09-18`;
- delivery identity: `7a05303ecd91804a7e315cb16be7bdea821fe475b12f4366d626f79d77cf4e40`;
- input identity: `24f8ae23ecd78fd3806af6908713e04b24eca5bdd4f9f090da231ade66ef203c`;
- pipeline identity: `9a4b1b913de9a0a8a2ddf2c953cc3bebf1c1bb90c760401ed491bd13311528fe`;
- local/end-remote main identity: `e40eb32253a03d62ce2c7bdd253762f824a54a26`;
- hard M6 checks: 50/50 true, zero errors;
- Phase21 real Chromium audit: 61/61 detail coverage, zero browser/future-node violations;
- no BSE candidate entered the default product scope.

The warning `partial_initialized_scope_allowed:55/5218` is intentionally not reclassified as an M6.2 blocker: M6.2 proves the initialized private-M1 operational chain, while M6.3 now owns the formal separation of listed / initialized / QFQ-ready / scanner / operator universes. The M4 research-QFQ warning likewise remains outside M6 operational authority.

CR-0066 is closed. No harmonic Source identity, Raw PRZ, lifecycle, M4 methodology, Outcome Engine, or trade-execution semantics were changed by this acceptance.
