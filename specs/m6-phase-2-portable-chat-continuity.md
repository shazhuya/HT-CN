# M6 Phase 2 — Portable Chat / Cross-AI Continuity v1

status: postmerge_pending
change: CR-0067
decision: D-067

## 1. Objective

Allow an empty ordinary ChatGPT conversation or another AI to recover HT-CN accurately from
one user-generated attachment, prove what it recovered, and continue without treating old
chat memory as project state.

## 2. Generated artifacts

The generator writes:

- `artifacts/reports/htcn-chat-continuation-bundle.zip` — preferred upload;
- `logs/context/HTCN_CHAT_HANDOFF.md` — standalone fallback when ZIP reading is unavailable;
- `logs/context/HTCN_NEW_CHAT_PROMPT.md` — first-message prompt;
- `logs/context/HTCN_CHAT_HANDOFF.sha256` — checksum for the standalone fallback.

These are generated views and remain outside Git. Canonical source and governance files stay
in the repository.

## 3. Bundle contract

The ZIP contains `MANIFEST.json`, `START_HERE.md`, the prompt, the dynamic Resume Pack and a
`canonical/` whitelist assembled from:

- Agent protocol, continuation protocol, Blueprint, README and CI workflow;
- Project State and all ledgers referenced by it;
- active Change and active spec;
- every `required_specs` entry;
- every active Decision source;
- the CR-0067 Change and bundle builder/verifier sources.

The manifest records repository, generation time, branch, HEAD, tree, locally observed remote
main, clean-worktree flag, current Project State identity, next task, privacy declarations and
the size/SHA-256 of every payload member.

## 4. Fail-closed generation

Normal generation requires:

1. Project OS validation is green;
2. every whitelist source exists, is a regular non-symlink file and stays under the repository;
3. the worktree is clean;
4. the completed ZIP passes the independent verifier against current HEAD.

`--allow-dirty` exists only for automated tests and implementation diagnostics. User-facing
BAT and CI must not use it.

## 5. Independent verification

The verifier rejects:

- invalid schema/kind or malformed manifest;
- unsafe paths, duplicate ZIP members or duplicate manifest paths;
- any missing or extra member;
- missing required authority files;
- forbidden private/runtime path prefixes;
- size or SHA-256 mismatch;
- Project State identity inconsistent with the manifest;
- current repository HEAD mismatch when `--require-current-head` is requested.

## 6. Bootstrap Receipt

Before implementation, the receiving AI must answer all eleven questions in
`CHAT_CONTINUATION.md`, including Git/state identity, Gate, human versus AI action, freezes,
support boundaries, recent Attempts, contradictions and allowed scope. Inability to answer any
item prevents a claim of lossless continuation.

## 7. Historical-chat boundary

Full-chat rereading is neither required nor authoritative. Targeted retrieval is allowed only
when the current request depends on a concrete user choice missing from the bundle. The AI
must identify the missing fact, retrieve only relevant history, reconcile it against higher
authority and persist any durable result before closeout.

## 8. Privacy and semantic freezes

The bundle must not include `data/`, `artifacts/`, `logs/`, `.git/`, private databases, market
payloads, screenshots, credentials, environment values or chat transcripts as canonical
payload. This feature must not alter Source identity, Raw PRZ, Source clock, M4 methodology,
Outcome Engine, product behavior or the M6.2 real-private evidence boundary.

## 9. CI acceptance

Every deterministic CI run builds and verifies the handoff after Project OS and tests. Main
runs publish the three user-facing artifacts for 30 days. Hosted construction proves only the
continuity mechanism; it does not prove a private-M1 run.
