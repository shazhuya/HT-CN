# M4 Phase 2.8 — Deterministic Methodology Identity

## Purpose

M4 prospective evidence must remain attributable to one frozen harmonic methodology.

A Git commit SHA is too broad for this purpose: documentation or unrelated infrastructure
changes may change `code_head` without changing candidate identity, Source Raw PRZ,
Source lifecycle or prospective enrollment semantics.

Phase 2.8 therefore adds a deterministic methodology fingerprint over the conservative set
of source files that can change those semantics.

## Authoritative identity

Every new committed capture uses capture transaction schema v2 and stores:

- `methodology_contract_version`;
- `methodology_fingerprint`.

The fingerprint is SHA-256 over an ordered set of per-file SHA-256 digests plus the
methodology contract version.

The transaction identity itself includes the methodology identity, so changing methodology
changes `transaction_id` even when market facts are otherwise identical.

## Chain continuity rule

One active M4 prospective committed-capture chain may contain exactly one methodology
identity.

Before appending a future transaction:

1. all existing committed transactions are read and validated;
2. pre-fingerprint schema-v1 transactions block append and require explicit migration;
3. a different methodology contract version or fingerprint blocks append;
4. the operator must start an explicitly versioned methodology epoch rather than mix
   evidence generated under different rules.

There is no automatic migration and no silent rebasing of old evidence.

## Current-code health gate

`m4_evidence_health` independently builds the methodology identity from the current
worktree and compares it with the authoritative committed chain.

A mismatch is a hard blocker:

`current_methodology_differs_from_committed_chain`

This does not mutate or invalidate historical committed evidence. It means the current code
may not continue that prospective chain until an explicit methodology-version decision is
made.

## Legacy T0 boundary

The frozen T0 baseline predates transaction-level methodology identity.

It remains valid as immutable baseline inventory / structural continuity evidence because it
is permanently excluded from prospective outcome inference.

It must not be rewritten merely to add a fingerprint.

## Compatibility mirrors and reports

Future snapshot-manifest compatibility rows expose methodology identity and mirror integrity
checks include it.

Derived transition / prospective-observation reports expose the authoritative methodology
fingerprint when committed transactions are active.

Compatibility mirrors remain non-authoritative and repairable.

## Source coverage

The fingerprint set intentionally includes the files that can affect:

- candidate / pattern identity;
- harmonic ratios and pattern rules;
- Source Raw PRZ;
- Source Terminal / lifecycle semantics;
- RSI BAMM evidence state;
- Shark / 5-0 source handling;
- M4 capture / prospective enrollment semantics.

The set is conservative by design. A methodology-affecting file must not be removed from the
fingerprint merely to avoid a future version boundary.

## Interpretation boundary

Methodology identity is evidence provenance, not a performance claim.

It does not establish:

- alpha;
- win rate;
- profitability;
- expected return;
- buy/sell ranking.

Those require a separately frozen future outcome protocol.


## Current supersession — Phase 2.10

Phase 2.8 originally introduced transaction schema v2 and methodology contract v1 before
any post-T0 fingerprinted future capture existed.

Before the first real T1 capture, Phase 2.10 expanded the frozen prospective evidence
semantics to cover scanner-absent outcome-cohort follow-up and capture chronology.

Current T1 protocol therefore uses:

- committed capture schema v3;
- methodology contract v2;
- 37 fingerprint components.

The additional fingerprint components are:

- `src/htcn/research/capture_transaction.py`;
- `src/htcn/research/cohort_followup.py`;
- `src/htcn/research/lifecycle_transitions.py`;
- `src/htcn/research/prospective_observations.py`;
- `src/htcn/research/snapshot_manifest.py`.

This is not a migration of existing post-T0 future evidence: none had been committed before
the v2 methodology freeze. The immutable T0 baseline remains unchanged.
