# CR-0066 — M6.2 Real Private-M1 Closeout

status: implementing
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
