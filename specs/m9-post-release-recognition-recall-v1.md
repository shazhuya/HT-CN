# M9 post-release — Harmonic recognition recall v1

status: planned

## Problem statement

HT-CN's authoritative harmonic engine is intentionally strict, but Stable product discovery incorrectly depends on that strict channel for whether a structure is visible at all. Real-market recall is therefore poor even when an XABC structure has a valid projected Source PRZ and is visually useful for monitoring.

## Required architecture

1. Preserve authoritative `completed` and `forming` outputs unchanged.
2. Add a separate `discovery` output for non-authoritative XABC candidates.
3. Default discovery pivot scales are 5/10/20, modeled after the standalone Pine behavioral baseline; callers may override later without changing Source identity.
4. Candidate graph may skip at most one complete minor swing pair per leg (pivot step 1 or 3) with a bounded recent search window. No arbitrary node stitching.
5. Candidate must satisfy turning topology plus the source structural B and C envelopes. Discrete C-family proximity is metadata/ranking, not a discovery existence gate.
6. Build PRZ only through the existing Source PRZ machinery. No discovery-specific Fib tables or PRZ rewrites.
7. Candidate remains discoverable for a bounded age after C instead of disappearing when a later pivot is confirmed.
8. PRZ test status starts no earlier than the C pivot's `confirmed_at` bar. No retrospective bars between C and C-confirmation may be donated.
9. A PRZ touch may be reported as `projected` or `tested`; it is not a canonical D, Source Terminal Price Bar, Type-I or Type-II.
10. Discovery ranking is presentation metadata only and can never rescue or mutate Source identity.

## Product behavior

- Candidate switcher includes authoritative structures first, then discovery-only structures.
- Discovery-only candidates are explicitly labelled `发现候选` and never display Source lifecycle or decision narrative as if formally qualified.
- Chart draws X-A-B-C and projected PRZ; it does not invent a D node.
- Audit shows path type (consecutive vs minor-swing skip), C family distance, candidate age, and PRZ-test status.
- Engine diagnostics expose authoritative completed/forming counts and discovery candidate count separately.

## Regression acceptance

- Existing authoritative tests remain unchanged and green.
- New tests prove: persistent historical XABC remains in discovery after a later pivot; a candidate with C inside the source structural envelope but outside the 3% discrete-family gate remains discovery-only; a two-pivot minor swing can be skipped; no PRZ test is backfilled before C confirmation; exact authoritative fixtures still dedupe correctly.
- Stable browser flow can select and render a discovery-only candidate when authoritative arrays are empty.

## Real-bar audit baseline carried into this implementation

Prior CR-0088 research established that the empty-product problem is observable on real daily bars, not merely a synthetic complaint. The audited datasets/hashes were:

- `寒武纪_每日详细数据_20260302-20260918.csv` — SHA-256 `c9cf5d984bab64aba02a532c230d5b0af3ddebb0748af95f9606568be14e6c29`, 140 daily rows.
- `cambricon_688256_daily_2025-09-03_2026-09-04.csv` — SHA-256 `b9507f92fe4fdba4ef1a5bc9c2d8257397533e0351386fe37e5784be8e0c8f3c`, 244 daily rows.

Production S3/5/8/13 returned zero current standard XABCD forming and zero standard XABCD completed on both audited daily samples. The 140-row raw sample had five historical B+C structural-band rule/window pairs but zero surviving the C discrete-family ±3% operational match. This is the concrete reason discovery existence may not be gated by discrete-family proximity.

These datasets are evidence references, not silently bundled proprietary/third-party market data. If their bytes are unavailable in CI, deterministic geometry fixtures must reproduce the measured gate boundaries and the real-data hashes/results remain in governance. A future same-timeframe Pine parity claim requires the actual 1-hour OHLC/basis/settings; daily data must never be substituted for that claim.

## Additional acceptance boundary

- The repair may be declared product-functional when the separate discovery channel, persistence, bounded topology, no-lookahead clock, API/UI separation and full hosted gates pass.
- It may **not** be declared Pine-hourly-equivalent until the exact hourly corpus is replayed under matched pivot/time/basis settings.
- Real-bar recall/false-positive statistics, if later published, require an explicitly labeled corpus and denominator; candidate count alone is not accuracy or trading performance.
