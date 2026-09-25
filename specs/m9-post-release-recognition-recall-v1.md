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
