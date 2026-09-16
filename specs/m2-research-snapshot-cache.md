# M2.13 — Pinned Research Snapshot Cache

## Problem

The M2 real-A-share calibration intentionally uses public QFQ providers rather than the
user's workstation database. The same pinned cutoff can nevertheless produce small run-to-run
changes when one provider fails over to another or later restates historical adjusted prices.
That makes sample expansion noisy and needlessly refetches long histories.

M2.13 freezes the **research input snapshot**, not the harmonic rules.

## Cache contract

Each symbol has two cached files under `artifacts/ci-research/data/`:

- `<instrument_id>.parquet`
- `<instrument_id>.snapshot.json`

The sidecar records instrument, QFQ mode, provider source, requested start, pinned cutoff,
maximum-bar capacity, first/last trading date and the exact parquet SHA256.

A restored snapshot is accepted only when:

1. sidecar schema and instrument match;
2. price mode is QFQ;
3. pinned cutoff exactly matches the current manifest;
4. cached requested start covers the current requested start;
5. cached bar capacity is at least the current request;
6. parquet bytes match the stored SHA256;
7. the parquet parses through HT-CN daily-data validation.

Any failure becomes a deterministic cache miss and the provider fetch path rebuilds that
symbol snapshot.

## GitHub Actions behavior

`actions/cache` uses the full research-manifest hash as the primary key and an M2 QFQ prefix
as a restore key. This permits an expanded same-cutoff manifest to recover already frozen
symbol snapshots while fetching only newly added symbols. Sidecar validation prevents an
old-cutoff restore from being trusted.

The cache is an execution optimization and reproducibility layer. The evidence artifact still
emits a standalone `m2-research-snapshot-manifest.json` containing each accepted snapshot's
source, cache status, date range, bar count and SHA256.

## Scientific boundary

- Cached provider data never changes Carney identity rules.
- A cache hit is not evidence that a pattern is good or profitable.
- Provider/source metadata is provenance, not a model feature.
- The completed-reaction 60/30/10/10 sample floor is not lowered to make the research pass.
- Holdout outcomes remain sealed exactly as in M2.12.

## Acceptance

M2.13 is accepted when deterministic tests show cutoff/capacity/hash invalidation works and a
second same-manifest CI run can reuse verified snapshots without refetching them. Manifest
expansion may then proceed incrementally against the same pinned cutoff.
