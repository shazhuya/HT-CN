# D-086 — M9.5 release identity is Git-fallback only and supervisor owns process lifecycle only

status: active
date: 2026-09-22

## Decision

M9.5 removes development tooling from normal product operation without weakening evidence provenance.

- When Git HEAD is available, Git remains the authoritative code identity. A dirty or unavailable Git status in a checkout remains fail-closed; HTCN_RELEASE_IDENTITY.json cannot launder it.
- Only a packaged runtime with no usable Git HEAD may use HTCN_RELEASE_IDENTITY.json.
- Packaged identity is valid only when the manifest fingerprint, exact protected-file SHA-256/size inventory and absence of unexpected protected files all verify.
- Formal release packaging is created from an exact clean Git head after the existing M4 methodology and Outcome Engine freeze guards pass.
- The package stores those 37/4 freeze results as build-time attestations. In a no-Git installed package, the freeze guards require both a verified release manifest and exact matching attestations; they do not re-derive or change frozen methodology.
- Formal CI must extract the built release ZIP into a directory with no .git and successfully run the M4 methodology guard, Outcome Engine guard and product-supervisor preflight there.
- The product supervisor owns process lifecycle only: API, static built Web, M9.1 market data, M9.2 harmonic runtime and M9.4 evidence service. It does not own their domain semantics.
- Normal daily Web serving uses built static assets. Vite/Node are development/build dependencies, not normal packaged runtime dependencies.
- Backup/restore/update may mutate only declared mutable product/research state or verified immutable release files according to their contracts. Release packages never contain private market data.
- M8 and ISSUE-0066 remain claims-only boundaries. No automatic trading is introduced.

## Failure boundary

Changed/missing/unexpected protected release files, invalid release attestations, future unknown product-state schema, unverified backup/update archives, critical supervisor crash-loop or failed post-update release verification fail closed and must not be hidden by automatic recovery.

## Non-goals

This decision does not change Carney identity, Source Raw PRZ, lifecycle, M4 methodology, Outcome Engine semantics, FIVE_ZERO quarantine, Alternate Bat fail-closed behavior, M7 no-backfill or statistical inference restrictions.
