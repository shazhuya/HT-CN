# M5 Phase 7 — Operator Cache Input Identity

## Scope

Phase 7 hardens the product-only Operator Queue cache so a same-day snapshot is reusable only
when the inputs that can change Queue output are still the same.

This phase does not change harmonic identity, Source Raw PRZ, Source lifecycle, M4 prospective
enrollment, Outcome Engine semantics, predictive ranking, or trade instructions.

## Problem

Before Phase 7, cache identity already covered:

- expected trade date;
- bars;
- scales;
- full initialized universe hash;
- cache contract version.

That is insufficient when, during the same trade date:

- M1 / delta / QFQ / benchmark / catalog data changes; or
- analysis code changes.

Reusing the old cache in those cases would return a Queue that no longer corresponds to the
current product inputs.

## Frozen identities

### Data Input Identity v1

Current product inputs:

- catalog.duckdb;
- catalog.duckdb.wal;
- daily parquet tree;
- daily_delta parquet tree;
- adjustment/qfq parquet tree;
- benchmarks parquet tree.

Manifest mode:

`relative_path_size_mtime_ns`

This is a product cache invalidation fingerprint, not authoritative research evidence.

### Analysis Code Identity v1

Content SHA-256 covers the explicit M5/M3 app + data dependencies and the recursive
`src/htcn/harmonic/**/*.py` analysis tree.

The API freezes this identity once per running process so a process never claims that newly
edited files on disk are the code it already loaded into memory.

### Operator Cache Input Identity v1

The combined fingerprint binds:

- data identity;
- analysis-code identity.

## Snapshot / cache contract

Operator snapshot contract version: **2**.

A cache hit must match:

- expected trade date;
- bars;
- scales;
- universe hash;
- snapshot contract version;
- combined input identity;
- data fingerprint;
- analysis-code fingerprint.

Any mismatch becomes a live rebuild, not an error and not a stale cache hit.

## Build-time stability gate

A rebuild records its starting input identity.

After the full Queue build, the current input identity is read again.

If the identity changed during the build:

- `input_identity_stable_during_build=false`;
- status becomes `live_not_cached_input_changed`;
- no product cache file is written.

This prevents a long full-universe scan from publishing a snapshot against inputs that changed
while the scan was running.

## Single-flight integration

The process-local single-flight key now includes the combined input fingerprint.

Therefore:

- identical current inputs may coalesce;
- different input identities must not coalesce;
- worker count still does not own Queue semantics.

Cross-process coordination is explicitly out of scope for Phase 7.

## Product/research boundary

Every Phase 7 identity remains:

- `authoritative_evidence=false`;
- `writes_m4_evidence=false`;
- `methodology_identity=false`.

No Phase 7 object may be interpreted as M4 evidence or a methodology fingerprint.

## Acceptance

Validated code checkpoint:

`7d1de7a81b7b2efc2a149eecd5a6c41b865123cd`

Latest hosted CI:

- workflow run: `35378357267` / #1634;
- overall: success;
- Python: 650 passed;
- Web build: success;
- Playwright: 21 passed;
- browser evidence upload: success.

The earlier user-referenced run `35378145254` / #1632 was cancelled because a newer push
superseded it; it is not treated as a code-test failure.

## Closeout

Phase 7 is green.

The next open product concurrency boundary is cross-process coordination between independent
API / precompute processes. Any Phase 8 solution must remain execution-only and must not change
Queue semantics or M4 evidence.
