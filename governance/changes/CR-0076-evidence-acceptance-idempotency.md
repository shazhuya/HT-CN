# CR-0076 — M7.5 Evidence Acceptance and Idempotent Rerun Contract

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 094ca01de6170a7e76ba1fb948996c26ed8bc940
target: main
milestone: M7.5

## Trigger

After the first M7 prospective capture was accepted, the same closed trading day was rerun on canonical main `094ca01de6170a7e76ba1fb948996c26ed8bc940`. The resulting bundle SHA-256 was `23b6b83c76653bc52f1508fcbd80fa6d09abf1b21c5dc6548f4ad209871cf3d4`.

The authoritative chain remained unchanged: one 2026-09-21 capture, transaction `9964d49a9147b404cedb4f2f`, and outcome snapshot `c348edab37a43eaaf7679299`. However, transport `code_head` advanced to `094ca01de6170a7e76ba1fb948996c26ed8bc940` while the immutable capture correctly retained origin `c822de2e30dce8b8aeefda31c183bb69148e835d`.

The current intake rule incorrectly treats those two identities as required to be equal.

## Objective

1. Separate bundle-generation identity from latest-capture origin.
2. Preserve backward compatibility for old bundles.
3. Add a read-only M7 acceptance engine that classifies `new_capture`, `idempotent_rerun`, or `not_ready`.
4. Fail closed on same-date transaction drift and capture-chain regression.
5. Keep all frozen research and inference boundaries unchanged.

## Non-goals

No automatic trade execution, no statistical inference, no change to capture methodology, Outcome Engine, Source rules, enrollment, or outcome semantics.

## Acceptance

See `specs/m7-phase-5-evidence-acceptance-idempotency.md`.

## Closeout

Merged through PR #64 as `1152d1fc80a78c2224cda6aa32c1bfdb80f21073`. Final ledger-bearing PR workflow `35590566473` / `#2454` and canonical-main workflow `35590805595` / `#2455` both passed all deterministic and formal release gates. ISSUE-0070 is closed; continuous M7 accumulation continues under ISSUE-0066.
