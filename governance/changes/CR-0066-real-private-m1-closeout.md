# CR-0066 — M6.2 Real Private-M1 Closeout

status: validation_green
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
