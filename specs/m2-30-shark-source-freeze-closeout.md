# M2.30 — Shark Source Raw PRZ / Terminal-Side Source Freeze Closeout

## Status

**Accepted.** Functional/research checkpoint: `e0f5d9334544944d00b232752ea0e8cdbf5c5bc8`.

GitHub Actions run #603 / `35186542998`: deterministic tests, web build, Playwright, 45-symbol real-A-share research, v6 boundary guard and frozen historical verifiers all passed.

## Why M2.30 existed

M2.26 already separated Shark from generic XABCD target management, but the source-aligned live execution path still needed an explicit answer to four questions:

1. What exactly is Shark Source Raw PRZ?
2. Which price bar is the source-aligned terminal observation?
3. How are Shark-specific reaction targets measured from that bar?
4. How can new Shark semantics enter current research without rewriting consumed historical evidence?

M2.30 closes those four questions without lifting 5-0 production quarantine.

## Frozen Shark source contract

Schema: `0-X-A-B-C`.

Source geometry remains:

- `A/0X = 0.382–0.618`;
- `B/XA = 1.13–1.618`;
- `C/AB = 1.618–2.24`;
- `C/0B = 0.886–1.13`.

### Source Raw PRZ

HT-CN freezes the Shark Source Raw PRZ as the geometric overlap/alignment of:

- `0B 0.886–1.13 completion corridor`;
- `AB 1.618–2.24 Extreme Harmonic Impulse corridor`.

If there is no overlap, source-aligned execution is unresolved and fails closed. No synthetic midpoint and no generic Ideal Core fallback is permitted.

`1.13 0B` remains the outer source completion / stop-limit reference.

## Source-aligned Terminal Price Bar

The live execution clock uses the observed price bar that tests the terminal side of the frozen Shark Source Raw PRZ. The later right-confirmed C pivot remains retrospective geometry/audit evidence and does not move the start of source execution.

This preserves the project-wide dual-clock rule:

`geometry history != execution observability`.

## Shark reaction management

At the observed Terminal Price Bar extreme:

- compute 50% of the B-to-Terminal completion leg;
- compute Reciprocal AB=CD from Terminal/C;
- initial target = whichever of those two lies closer / is encountered first from Terminal/C;
- 61.8% BC is the wider prospective 5-0 management level when applicable.

These target measurements are management-only. They do not participate in Shark identity or Source Raw PRZ membership.

## 5-0 relationship

M2.29 remains authoritative:

- structural 5-0 Source Raw PRZ = `50% BC + Reciprocal AB=CD`;
- Volume Three 61.8 = execution refinement / stop reference only;
- the V3 XA/AB/BC label inconsistency is preserved as a source conflict;
- production Engine / Scanner / Workbench quarantine remains on.

M2.30 does not use Shark completion as a back door to enable production 5-0.

## Research version governance

Current definition: `m2-source-prz-v6`.

Historical versions remain immutable:

- v1 historical Type-I prereg/result;
- v3 standard-XABCD Source Raw PRZ;
- v4 standalone AB=CD Source Raw PRZ;
- v5 reconciled 5-0 structural research contract.

The v6 guard explicitly verifies that historical Holdout / external replication records are not recomputed or relabelled.

## Real A-share v6 evidence

Dataset: `a-share-research-v2-45`, cutoff `2026-09-15`.

Run #603:

- snapshot cache: 45 hit / 0 miss;
- forming signals: 8244;
- mature Source-Raw-PRZ Terminal events: 1499;
- purged: 35;
- Train / Validation / sealed Holdout: 871 / 265 / 328;
- Shark terminal events: 76 / 26 / 40;
- Terminal observed: 1509;
- Source PRZ unresolved: 189;
- visible Type-I robustness: `full_prz_exit_by_t3`, `full_prz_exit_by_t5`;
- completed-reaction robust candidates: none;
- confirmatory inference allowed: false.

The visible v6 statistics are research evidence only. They are not current-stock probabilities, mechanical entry rules or Carney source rules.

## CI resilience repair accepted with M2.30

The previous 40-minute cancellation was an infrastructure failure, not evidence that Shark scanning was computationally unusable.

Root cause:

- GitHub token lacked Actions artifact read permission;
- frozen snapshots therefore failed to restore;
- the 45-symbol decade-long QFQ dataset was repeatedly re-fetched;
- a 40-minute job timeout killed the run before completion.

Repair:

- add `actions: read`;
- bootstrap the known frozen 45-symbol artifact on cache miss;
- persist the bootstrap immediately to cache;
- use independent non-cancelling concurrency for long research;
- retain cancelling concurrency for short deterministic feedback;
- use unbuffered progress output;
- use 90-minute timeout as guardrail, not as a substitute for optimization.

Validation: after restoration, the 45-symbol calibration completed in about 85 seconds and the entire research job in about two minutes.

## Exit criteria

M2.30 is closed because:

- [x] Shark Source Raw PRZ has source-backed explicit membership;
- [x] unresolved alignment fails closed;
- [x] source Terminal Price Bar is separated from retrospective C pivot;
- [x] Shark target semantics are separate from generic XABCD;
- [x] Book Golden and negative tests exist;
- [x] v6 research boundary is sealed;
- [x] historical closed evidence remains immutable;
- [x] real A-share v6 CI is green;
- [x] research snapshot recovery is proven operational.

## Next Gate

**M2.31 — RSI BAMM Dedicated Source State Machine.**

Ordinary Wilder RSI oversold/overbought evidence must remain explicitly non-BAMM until the full Carney BAMM sequence, temporal ordering, invalidation and no-lookahead tests are implemented.
