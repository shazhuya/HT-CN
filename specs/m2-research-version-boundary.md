# M2 Research Version Boundary

## Purpose

M2.26 changes source-fidelity and identity semantics. Those changes alter which historical events
are eligible for downstream Type-I research. Therefore the already-consumed M2 Type-I Holdout
and external replication are historical evidence for their original frozen engine definition only.
They must never be silently rebuilt with the M2.26 runtime and treated as the same confirmatory
study.

## Historical v1 — immutable consumed evidence

Historical Type-I v1 is frozen by:

- preregistration: `research/m2-type-i-holdout-prereg-v1.json`;
- frozen evidence commit: `bc90af32963498d174aa2470852ec40330be7853`;
- preregistered Holdout records: `355`;
- one-time frozen result: `research/m2-type-i-holdout-result-v1.json`;
- closed authorization: `research/m2-type-i-holdout-open-v1.json`;
- external replication preregistration/result files under `research/`.

Rules:

1. v1 is consumed and closed.
2. Current runtime must not rebuild the v1 preregistration.
3. Current runtime must not reopen or recompute the v1 Holdout result.
4. v1 result files may be checked only for static integrity and cross-file consistency.
5. No M2.26 sample count or outcome may replace a v1 number.

## Source-fidelity v2 — current research definition

The M2.26 runtime applies repaired source-fidelity semantics, including discrete harmonic-family
identity checks and stricter separation of source PRZ, ideal core and component envelope.
Consequently, historical event membership can differ from v1.

During the first M2.26 full 45-symbol calibration after the repair, the sealed Type-I timing
Holdout contained `313` records versus the historical v1 preregistered `355`. This difference is
expected evidence of a definition/version change; it is not a number to retrofit into v1.

Current v2 policy:

- Holdout remains sealed;
- `outcomes_exposed=false`;
- `holdout_opened=false`;
- no confirmatory inference is permitted;
- no policy freeze is permitted from this reused historical dataset;
- v2 cannot replace, rescue, invalidate or reinterpret the historical v1 confirmatory result;
- a new v2 confirmatory claim requires a separately preregistered untouched future dataset or
  prospective period.

## CI contract

The M2 push research job uses two independent tracks:

### Current v2 research track

1. build current 45-symbol calibration evidence;
2. keep the v2 Holdout sealed;
3. run `scripts/m2_source_fidelity_research_guard.py`;
4. emit `artifacts/ci-research/m2-source-fidelity-v2-boundary.json`;
5. make no confirmatory claim.

### Historical v1 integrity track

1. `scripts/m2_type_i_holdout_prereg_report.py` verifies the frozen historical preregistration
   statically and does not read current calibration;
2. `scripts/m2_type_i_holdout_result_report.py` verifies the consumed one-time result and its
   closed authorization without recomputation;
3. external replication preregistration/result verifiers remain static historical integrity
   checks.

Cross-version runtime reconstruction is prohibited.

## Snapshot cache policy

Real A-share calibration can require fetching 45 long QFQ histories. A later scientific integrity
failure must not discard already-validated market-data snapshots and force an unnecessary provider
refetch.

CI therefore restores the research cache before calibration and saves it immediately after a
successful calibration, before later research-integrity gates run. Cache reuse affects only data
retrieval cost; it does not change identities, samples, outcomes or statistical rules.

## Acceptance invariant

A green M2.26 research gate means all of the following simultaneously:

- current source-fidelity v2 calibration executed successfully;
- current v2 Holdout remained sealed and was not used for confirmatory inference;
- historical v1 preregistration/result remained immutable and closed;
- historical external replication remained immutable;
- no cross-version sample-size substitution or optional stopping occurred.
