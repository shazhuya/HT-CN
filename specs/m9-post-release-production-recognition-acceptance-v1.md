# M9 post-release — Production recognition acceptance v1

status: closed

## Product completion definition

Recognition is complete only when a user can open a real A-share on 1D/60m/15m, see persistent useful developing structures across the supported families, inspect projected completion/PRZ measurements, and obtain the same deterministic behavioral result as the retained Pine R3.4 baseline on identical OHLC/settings.

## Channels

### pine_r34
Exact deterministic behavioral baseline. It owns parity acceptance but does not own canonical Carney/Source truth.

### extended_graph
HT-CN supplementary high-recall graph discovery. It may find additional XABCD paths and must be labelled supplementary.

### authoritative
Existing frozen completed/forming Source identity/lifecycle. It remains unchanged.

## Supported behavioral discovery

- Gartley
- Bat
- Butterfly
- Crab
- Deep Crab
- Deep Gartley behavioral candidate
- Alternate Bat behavioral candidate (research-only because canonical source conflict remains)
- standalone AB=CD x1
- standalone AB=CD x1.27 / x1.618 (research/reference)
- Shark
- 5-0 (research-only while ISSUE-0067 remains open)

## Intraday contract

- supported product timeframes: 1d, 60m, 15m;
- 1d continues to use canonical local daily + QFQ basis;
- intraday data is stored separately with timeframe, provider, adjustment mode, fetched_at and data-range provenance;
- provider failures use bounded retry/failover; stale/missing data is visible and never fabricated;
- intraday recognition does not inherit a daily Source lifecycle.

## Real-market acceptance corpus

The hosted acceptance corpus is a fixed diversified SSE/SZSE set spanning large-cap, growth, STAR, finance, consumption, industrial, resources and high-beta technology. The report must include denominator, successfully fetched series, failed series, candidate counts by family/timeframe/channel, and exact parity mismatches.

A provider outage may fail data coverage explicitly; it may not be reclassified as recognition success.

## Release gate

No `ready_to_merge` until:
- deterministic family parity green;
- no-lookahead walk-forward green;
- intraday provider/cache/API/UI tests green;
- real-market hosted acceptance report green;
- full existing Stable/M4/Outcome gates green.
