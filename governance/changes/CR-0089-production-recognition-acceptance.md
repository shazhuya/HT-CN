# CR-0089 — Production recognition acceptance and Pine R3.4 parity

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: d795773f20956021878f812cdbf6c49e491edb86
target: main
milestone: M9.post_release
work_branch: m9/production-recognition-acceptance-v1

## Trigger

Direct user rejection of partial delivery: CR-0088 repaired the standard-XABCD existence gate, but Stable is not accepted as practical until recognition is proven on real A-share data and the Pine R3.4 behavioral baseline is reproducible on matched inputs.

## Objective

Deliver one practical recognition system rather than another architecture-only milestone:

- reproduce the standalone Pine R3.4 recognition behavior deterministically from raw OHLC;
- cover standard XABCD, standalone AB=CD, Shark and research-only 5-0 discovery;
- add 15-minute and 60-minute A-share data access with provenance/failover and local caching;
- expose timeframe selection in the Stable research workspace;
- keep Source/canonical identity separate from Pine-behavioral discovery;
- build hosted real-market acceptance and machine-readable mismatch reports;
- keep iterating until deterministic parity and real-market acceptance gates are green.

## Pine behavioral baseline

Reference: `Ashare_Harmonic_Radar_R3_4.pine`
SHA-256: `84e1eb2267c9b80891e0ffb64a6d4abf5712fc5e756be81815e536f2fca4c3f5`

Frozen recognition inputs:
- pivot confirmation strengths 5 / 10 / 20;
- ATR(14), minimum leg 0.35 ATR;
- maximum source span 500 bars;
- completion-envelope width <= 0.12 of reference leg;
- persistent structure lifetime 180 bars;
- no retrospective PRZ-test backfill before the structure is knowable;
- family-specific completion projections and structure limits from R3.4.

## Hard acceptance

This Change must not close merely because CI compiles.

1. Deterministic Pine-parity fixtures for every supported family must match source-node indices, direction, projected measurements/PRZ and research/qualified status.
2. A walk-forward replay must prove no future pivot or historical PRZ-test backfill enters a candidate before its Pine-equivalent knowable bar.
3. Stable must support 1D / 60m / 15m analysis without requiring the user's computer.
4. Hosted real-A-share acceptance must use a fixed diversified corpus, publish provider coverage, candidate counts and mismatch details, and fail on parity mismatches for the supported behavioral channel.
5. CR-0088 extended-graph discovery may add supplementary candidates but must never silently replace or mutate the Pine-parity baseline.
6. Standard XABCD, AB=CD and Shark must be practically discoverable. 5-0 may be shown only as research discovery while ISSUE-0067 remains unresolved; it must not acquire Source lifecycle/trade status.
7. UI must distinguish behavioral-parity vs supplementary candidates, show timeframe/data provenance, and sort practical monitoring candidates by PRZ proximity without confusing distance with identity quality.
8. Frozen M4 methodology, Outcome Engine, Source Raw PRZ, canonical CARNEY_RULES identity and no-auto-trading boundary remain unchanged.

## User-computer boundary

Routine development, data acquisition, parity testing and CI must run in hosted/cloud infrastructure. The user's Windows machine is not an acceptance dependency. A user-side TradingView export may be requested only if a TradingView-private output cannot be reproduced from the retained Pine R3.4 source and matched OHLC.


## Validation history

### A-20260925-0089-001 — planned candidate hosted validation

- head: `bb45ff25a0c112cf0b092c102b22b29a34b4561e`
- workflow: `36107602296 / #2918`
- result: success
- covered: Project OS, Source Coverage, zero-debt Ruff, full Python suite including new Pine R3.4 and intraday provider tests, continuation bundle build, Node/Web production build.
- interpretation: sufficient to activate this Change; **not** sufficient to close it. Real A-share acceptance, targeted browser acceptance and final frozen release gates remain required.


### A-20260925-0089-002 — production recognition acceptance

- head: `f6ec535039b7ff86275a1a305531aabbc6427efa`
- workflow: `36114380454 / #2982`
- result: success
- deterministic: Ruff 0; Python 1046/1046; Web production build; targeted browser 5/5.
- hosted real market: 30/30 successful series across 10 diversified A-shares × 1D/60m/15m; stale series 0.
- recognition: 4482 historical births; 803 stored standard candidates; 230 practical monitoring candidates; 53 practical standard candidates; all three timeframes contain standard monitoring output.
- noise control: per-series monitoring bounded to <=12; 199 remote candidates filtered.
- R3.5 practical overlay: 268 real-market neighborhood observations; 92 neighborhood reactions; 195 later strict-test takeovers. Neighborhood never expands strict PRZ or fabricates T-Bar/Type-I/Type-II.
- user computer: not used.
- decision: recognition hard acceptance is satisfied; advance to `ready_to_merge` and require formal PR release/frozen-boundary validation before merge.
