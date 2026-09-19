# D-068 — Universe layers are explicit, hashed and non-interchangeable

status: active
change: CR-0068
date: 2026-09-20

## Decision

HT-CN freezes distinct universe semantics for the default SSE/SZSE scope:

1. `listed_universe` comes from listed security-master identity.
2. `initialized_universe` is the listed subset with valid catalog daily-dataset metadata and an existing local base Parquet.
3. `formal_qfq_ready_universe` is the initialized subset whose existing continuous-price semantics resolve to `qfq` or `qfq_carry_forward` with a `qfq:` basis.
4. Product `scanner_universe` equals initialized_universe.
5. Formal research `research_scanner_universe` equals formal_qfq_ready_universe.
6. `operator_universe` must exactly equal product scanner_universe.
7. Harmonic candidate sets are downstream outputs and are never coverage denominators.

BSE remains deferred from the default scope. UI limits, filters, watchlists and local orphan files do not define scanner coverage.

Default-scope parentage errors fail closed: an SSE/SZSE initialized member not present in listed_universe, or a formal-QFQ member not present in initialized_universe, is an invariant failure rather than a silently filtered condition.

## Rationale

The accepted M6.2 real Private-M1 closeout was operationally valid with 55 initialized SSE/SZSE instruments against 5218 listed instruments. That is a real coverage gap, not a reason to call the product broken and not permission to call the initialized subset full-A-share coverage.

Freezing the vocabulary prevents product readiness, research readiness and market breadth from being conflated.

## Boundaries

This decision does not bulk-initialize market data, repair QFQ factors, enable BSE, alter harmonic Source identity/Raw PRZ/Source Clock/Reaction-Reversal semantics, change M4 methodology or Outcome Engine, execute trades, or authorize win-rate/alpha/profitability claims.
