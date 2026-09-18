# M4 Phase 2.5 — Atomic Committed Capture Evidence

## Problem

Two independent append operations cannot form a true atomic snapshot.

Old flow:

1. append lifecycle journal;
2. append snapshot manifest.

An interruption between them can produce half-state.

## Authoritative transaction

Future captures are wrapped into one immutable committed JSON file.

Transaction identity includes:

- capture schema version;
- methodology contract version + deterministic methodology fingerprint;
- code head;
- as-of trade date;
- complete instrument coverage;
- canonical sorted candidate facts.

It excludes wall-clock capture time so identical reruns stay idempotent.

From Phase 2.8 onward, new authoritative captures use transaction schema v2. An active
prospective chain may contain only one methodology identity; methodology drift fails closed
and requires an explicitly versioned new methodology epoch.

## Commit protocol

1. analyze all selected instruments;
2. require zero instrument failures;
3. build canonical capture payload;
4. compute deterministic transaction id;
5. write temp transaction file;
6. flush + fsync;
7. atomically os.replace to final committed filename;
8. only then attempt compatibility journal/manifest mirrors.

If mirror update fails, committed transaction remains authoritative.

## Legacy migration

Before the first transaction, the old prospective T0 journal is frozen into an immutable legacy baseline.

The baseline carries a cutoff date.

Future transactions must be strictly later than that cutoff.

This prevents newer code from silently re-running or replacing T0.

## Downstream evidence

After transaction activation:

- transition reports;
- prospective observation reports;

read frozen baseline + committed captures only.

Compatibility mirrors are not authoritative.

## Fail-closed conditions

- partial instrument coverage;
- dirty worktree;
- same-date different transaction;
- transaction historical backfill;
- capture date <= frozen baseline cutoff;
- transaction-id mismatch;
- transaction filename mismatch;
- per-row transaction-id mismatch;
- duplicate candidate key;
- alpha/trade-instruction boundary violation;
- unsupported schema;
- mutated frozen baseline.

## Interpretation

Atomicity here protects evidence integrity.

It does not establish alpha, win rate, profitability or trade execution.
