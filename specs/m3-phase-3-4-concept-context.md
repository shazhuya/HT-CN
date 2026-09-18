# M3 Phase 3.4 — Concept / Theme Context

## Semantic difference from industry

Industry is expected to be close to one primary membership per source and fails closed on same-source ambiguity.

Concept/theme membership is intentionally multi-valued. A security may legitimately belong to many concepts. HT-CN therefore stores every audited membership instead of collapsing them into one concept.

## Data source and refresh

Membership source:

- AKShare / Eastmoney `stock_board_concept_name_em`
- AKShare / Eastmoney `stock_board_concept_cons_em`

Because concept count is much larger than industry count, membership refresh uses bounded concurrency (default eight workers) and retries. Replacement remains all-or-nothing: any unresolved concept fetch preserves the prior complete mapping.

Default membership refresh interval is seven days.

## Local evidence

Concept returns, breadth and volume are recomputed from local M1 constituent bars using the same transparent aggregate contract as industry context.

For each concept attached to the analyzed security, HT-CN exposes:

- 5 / 20-session concept median return;
- MA20 breadth;
- one-day up breadth;
- average 20-session constituent volume ratio;
- security relative 5 / 20-session return versus that concept median.

Concept display ordering is raw `median_return_5d_pct DESC`. It is not a composite score or a recommendation.

## Frozen product boundaries

- multi-concept membership is normal, not an ambiguity failure;
- `mutates_harmonic_identity=false`;
- `mutates_source_raw_prz=false`;
- `owns_lifecycle=false`;
- concept/theme evidence cannot rescue a failed harmonic identity.
