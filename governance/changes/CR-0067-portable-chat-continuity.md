# CR-0067 — Portable Chat / Cross-AI Continuity

status: closed
baseline_ref: main
baseline_head: 704b0b631ffc6592e20f56324119068096da8bcd
target: main
milestone: M6.2

## Problem

Project OS v2 made the repository authoritative, but the user-facing handoff was still one
generated Markdown index. A new ordinary ChatGPT conversation or another AI could lack a
GitHub connection, omit a required ledger, trust a stale attachment, or start changing code
before proving that it had recovered the current project boundary.

Repeatedly rereading every old conversation is not a reliable solution: it is slow, not
portable across AI products, and allows historical discussion to override current Git and
governance truth.

## Required result

1. One Windows action builds a portable ZIP, a standalone Markdown fallback and a ready-to-
   paste new-chat prompt.
2. The ZIP is whitelist-only and binds every member to a size and SHA-256 manifest.
3. The bundle records Git HEAD/tree and the current Project State identity.
4. A standalone verifier rejects missing, extra, duplicated, unsafe or modified members and
   can require the current repository HEAD.
5. A new AI must return a structured Bootstrap Receipt before changing code.
6. The mechanism works without chat history and without a GitHub connector.
7. Old chats are consulted only for a specifically missing user decision; recovered facts
   must be persisted into repository governance before closeout.
8. Private M1 data, runtime evidence, credentials, environment variables and raw chat history
   are never included.
9. CI builds and verifies the portable handoff so the contract cannot silently rot.

## Acceptance criteria

- `CHAT_CONTINUATION.md` defines the user flow, recovery order, eleven receipt questions,
  targeted old-chat policy and closeout rule.
- `scripts/build_chat_continuation_bundle.py` builds all three user-facing artifacts from
  repository truth and rejects dirty worktrees by default.
- `scripts/verify_chat_continuation_bundle.py` performs fail-closed independent verification.
- `生成HT-CN续接包.bat` is the single generation entrypoint and
  `验证HT-CN续接包.bat` is the local verification entrypoint.
- Automated tests cover success, required authority/spec inclusion, extra members, duplicate
  members and content tampering.
- Project OS, Python tests/warning budget, Ruff budget and Web build stay green.

## Non-goals

This Change does not close M6.2, execute the real private-M1 run, modify harmonic identity,
Source truth, M4 methodology, the Outcome Engine, research evidence, product semantics or
trading behavior. It does not put private artifacts or complete chat transcripts into Git.

## Closure boundary

CR-0067 may close as a parallel Project OS enhancement while CR-0066 remains the active
M6.2 Change in `awaiting_private_run`. Closing this Change must not change the M6.2 evidence
Gate or claim that real private-M1 acceptance occurred.

## Local validation

- Project OS: ready, with the known D-065 legacy-context historical warning only;
- Python: **878 passed / 0 warnings**;
- Ruff: **483 / budget 483**, no new debt;
- Web production build: success;
- M4 capture methodology: **frozen_match / 37 components**;
- Outcome Engine: **frozen_match / 4 components**;
- portable handoff: **37 whitelisted entries**, build and independent HEAD-bound verification
  succeeded;
- failures A-20260919-0067-001 through 003 remain preserved and their guards were not weakened.

Hosted PR #43 run `35451049509` / #2144 passed both deterministic tests and
`formal-main-release-integrity`; artifact `10587105797` preserves the formal evidence. The
portable bundle build/verification step passed in the hosted environment. Merge and post-merge
main validation remain required before closure.

PR #43 was squash-merged as `335414530850bd5b4d5acf030c7eff49cf5f9124` with the exact
final hosted branch tree. An explicit main push validation is pending before closure.

The GitHub App merge/ref update did not emit a main push workflow. This connector limitation is
preserved as A-20260919-0067-007; a final governance-only PR must validate the exact closeout
candidate through `formal-main-release-integrity` before the Change can close.

## Final closeout

- implementation merge: PR #43 / `335414530850bd5b4d5acf030c7eff49cf5f9124`;
- final implementation PR validation: run `35451245127` / #2146, success;
- postmerge candidate validation: PR #44, run `35451544343` / #2150, success;
- formal artifact: `10586688451`;
- final closed-state candidate must pass the same two hosted jobs before PR #44 merges;
- CR-0066 remains the active Change, M6.2 remains `awaiting_private_run`, and no real
  private-M1 acceptance is claimed.

## Ledger reconciliation

A blank-session bootstrap audit found that the final closed-state validation and merge were present in GitHub but had not been appended to the Attempt Ledger. The missing immutable facts are now reconciled:

- A-20260919-0067-009: final closed-state head `8393f5fb660c973eb7b29c022f4083704530d658`, PR #44 run `35451731667` / #2152, success for both `deterministic-tests` and `formal-main-release-integrity`;
- A-20260919-0067-010: PR #44 merged as canonical main `5a13109c987eb8dfe08a282e977ad2f4f7cfddff`;
- no CR-0066, M6.2 Gate, Source, M4 methodology, Outcome Engine, product or research semantics changed.

