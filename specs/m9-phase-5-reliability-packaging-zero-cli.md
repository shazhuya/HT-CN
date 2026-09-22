# M9.5 — Reliability, Packaging & Zero-CLI Operation

status: implementing

## 1. Objective

Deliver the product-runtime layer that removes development tooling from normal HT-CN use while preserving auditability and recovery.

## 2. Verified release identity

Development checkout:
- Git HEAD + clean-worktree remains authoritative.
- If Git HEAD is available, packaged identity must never override it.
- A dirty worktree remains fail-closed.

Packaged install:
- package contains a machine-readable release identity manifest with release head and SHA-256 file inventory;
- when no Git repository is available, code identity is valid only if the release manifest exists and every declared immutable file matches;
- missing, changed or extra protected files fail closed and prevent authoritative M4 evidence capture;
- evidence capture continues to receive a stable code_head and worktree_clean=true only after manifest verification.

## 3. Release package

A deterministic package builder must:
- require a clean release source identity;
- include Python source/scripts/services, built Web assets, launch/recovery entry points and runtime metadata;
- exclude mutable data, caches, logs, credentials and private market data;
- emit the verified release identity manifest and package SHA-256;
- provide a verifier that can run without Git.

Normal packaged daily use must not require Node/Vite.

## 4. Product supervisor

One supervisor owns product process lifecycle only; it does not own market/harmonic/evidence semantics.

Children:
- API;
- static Web server;
- M9.1 market-data scheduler;
- M9.2 harmonic runtime;
- M9.4 background evidence service.

Requirements:
- bounded exponential restart backoff;
- crash-loop detection;
- graceful stop;
- one supervisor lock;
- atomic status with PID/process state/restart count/last error/Chinese remediation;
- healthy/degraded/blocked aggregate state;
- child logs separated by service;
- no shell windows required in normal background startup.

## 5. Backup, restore and migration

Product state classes:
- authoritative research state and product state: backed up;
- rebuildable runtime caches/logs: excluded;
- private raw market data: never uploaded or included in release artifacts.

Backup:
- deterministic archive manifest with SHA-256 inventory;
- pre-update snapshot;
- retention policy;
- atomic completion marker.

Restore:
- verify backup manifest before mutation;
- stage restore, reject traversal/tampering, preserve a pre-restore snapshot;
- restore only declared mutable product/research state;
- never modify immutable release files.

Migration:
- schema/version field in product state;
- idempotent migration registry;
- fail closed on unknown future schema.

## 6. Update path

M9.5 provides a verified local update-package apply path:
1. verify update package release identity and package digest;
2. create pre-update backup;
3. stop product services;
4. stage immutable release replacement;
5. preserve mutable data;
6. verify new release identity;
7. restart product and expose success/failure status;
8. rollback immutable release files on failed verification.

Network discovery/download of a future release may be added later; no CLI is required to apply a verified pending package.

## 7. User entry points

Normal Windows product entry points are one-click wrappers:
- install/update;
- start;
- stop;
- backup;
- restore/recovery.

They may call Python internally but the user does not type commands or manage Git/Node/Vite.

## 8. Observability

Expose product status with:
- release identity source/head/integrity;
- supervisor state and child states;
- last successful backup;
- pending recovery/update fault if any;
- Chinese remediation text.

No statistical claim fields are added.

## 9. Tests

Hosted deterministic coverage must include:
- Git clean/dirty precedence over packaged manifest;
- package identity verification without .git;
- changed/missing protected file fail-closed;
- deterministic package inventory;
- supervisor restart/backoff/crash-loop state;
- static-Web/no-Vite runtime contract;
- backup manifest round-trip and tamper rejection;
- restore path traversal rejection;
- schema migration idempotency/future-schema fail-closed;
- API/UI product status rendering;
- all existing browser, Phase18/21 and frozen 37/4 gates remain green.

## 10. Exit gate

M9.5 may close only when:
- normal install/start/update/recovery requires no typed command line;
- daily product start uses supervisor + built Web, not Vite dev server;
- backup/restore/migration are productized and verified;
- provider/runtime failures have automatic restart or explicit Chinese remediation;
- daily usage requires no ZIP handoff or AI manual acceptance;
- packaged authoritative evidence uses verified release identity without an interactive Git worktree;
- no user-computer validation is required for the phase.
