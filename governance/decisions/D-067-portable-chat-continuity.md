# D-067 — Portable, receipt-gated continuity replaces full-chat rereading

status: active
change: CR-0067
date: 2026-09-19

## Decision

HT-CN continuation across ordinary ChatGPT conversations or different AI systems uses a
repository-generated, whitelist-only handoff bundle containing:

1. a manifest with Git identity plus per-file size and SHA-256;
2. current Project OS recovery material and required canonical files;
3. a standalone Markdown fallback;
4. a ready-to-paste new-chat prompt; and
5. a mandatory eleven-item Bootstrap Receipt before implementation begins.

Complete old-chat rereading is not a standard bootstrap step. Old chats are secondary,
targeted recovery evidence only when a concrete user choice is missing from canonical
records. Any recovered durable fact must be written to Change, Decision, Issue, Attempt or
State before the work unit closes.

The bundle must exclude raw private-M1 data, runtime evidence, secrets, environment values
and chat transcripts. Lack of GitHub access must be declared, never disguised as an online
verification.

## Rationale

A new AI needs a small, explicit and independently checkable representation of current truth,
not an ever-growing conversational archive. Binding the handoff to repository state reduces
semantic drift while preserving the ability to recover a rare, previously unrecorded user
decision from chat history.

## Consequences

- Git and Project OS remain authoritative over every handoff artifact.
- A stale or contradictory bundle blocks core work until reconciled.
- New chats can start from an uploaded file even when no repository connector is available.
- The generated artifacts are disposable views; durable facts still live in canonical Git.
