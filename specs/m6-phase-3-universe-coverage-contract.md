# M6.3 — Universe Coverage Contract

status: implementing

## 1. Objective

Freeze one machine-readable vocabulary for HT-CN market coverage so the project never
confuses "all listed A shares" with "locally initialized", "formal-QFQ ready",
"scanner input", "operator input", or the downstream harmonic candidate set.

This phase exists because the accepted M6.2 real Private-M1 run was operationally ready
with 55 initialized default-scope instruments against 5218 listed SSE/SZSE instruments.
That fact is a coverage gap, not permission to describe 55 instruments as full A-share
coverage and not, by itself, a product failure.

## 2. Canonical layers

The default production scope is SSE + SZSE. BSE remains deferred.

1. **listed_universe**
   - Source: `security_master.status = listed`.
   - Scope: default exchanges only.
   - Meaning: securities currently listed according to the local security master.

2. **initialized_universe**
   - Must be a subset of listed_universe.
   - Requires a catalog `daily_dataset` record with positive rows, valid date range,
     and an existing local base Parquet.
   - A file merely existing in `data/market/daily` does not initialize an instrument
     if catalog/listed identity does not agree.

3. **formal_qfq_ready_universe**
   - Must be a subset of initialized_universe.
   - The existing continuous-price logic must resolve to `qfq` or
     `qfq_carry_forward` with a `qfq:` basis identity.
   - Raw fallback is not formal-QFQ-ready.

4. **scanner_universe**
   - Product scanner input.
   - Default contract: exactly initialized_universe.
   - UI display limits, queue filters, watchlists, or candidate counts never define it.

5. **research_scanner_universe**
   - Formal research/statistical scanner input.
   - Exactly formal_qfq_ready_universe.
   - This preserves the M4 QFQ boundary instead of weakening it to make product
     coverage appear larger.

6. **operator_universe**
   - Exact instrument set passed into the M5 Operator Queue.
   - Must equal scanner_universe.
   - A mismatch is a contract failure.

7. **candidate_set**
   - Downstream harmonic matches produced after scanning.
   - It is not a universe and must never be used as a coverage denominator.

## 2.1 Parentage integrity

Same-exchange parentage is fail-closed. For the default SSE/SZSE scope:

- an initialized input member absent from listed_universe is an invariant failure;
- a formal-QFQ-ready input member absent from initialized_universe is an invariant failure;
- these errors must be reported explicitly and must not be hidden by intersection/filtering;
- BSE is different: it is intentionally outside default scope and remains reported as deferred rather than treated as a parentage error.

## 3. Default exchange boundary

- `SSE.*` and `SZSE.*` are the default scope.
- `BSE.*` is reported separately as deferred coverage and must not enter the default
  product scanner or operator universe.
- M6.3 does not delete BSE data or remove future BSE capability.

## 4. Coverage claims

Every coverage-bearing report must identify the exact layer, count and deterministic
instrument-set hash.

Prohibited wording/semantics:

- initialized universe == full A-share universe;
- scanner universe == all listed securities when listed coverage is incomplete;
- candidate count == scanner coverage;
- raw-price fallback == formal-QFQ-ready;
- a UI limit or shortlist == scanner universe.

Coverage gaps are first-class facts. They may become blockers only where a downstream
contract explicitly requires full coverage.

## 5. Product / research separation

M5 daily product operation may remain ready when initialized coverage is partial, as
M6.2 demonstrated. The product must report that partial coverage explicitly.

M4 authoritative research continues to require its formal-QFQ boundary. M6.3 does not
modify M4 capture methodology, Outcome Engine, Source identity, Raw PRZ, Source Clock,
Reaction/Reversal semantics, or any trading rule.

## 6. Machine implementation

Required implementation:

- `src/htcn/app/universe_coverage.py`
  - deterministic layer definitions and hashes;
  - read-only catalog discovery;
  - optional formal-QFQ readiness assessment;
  - invariant checks and gap reporting;
  - iterable inputs must be materialized deterministically so list/tuple/generator
    inputs cannot change hashes or deferred-scope reporting;
  - candidate_set must be emitted as a downstream machine-readable set with
    coverage_denominator=false.
- `scripts/m6_universe_coverage.py`
  - writes `artifacts/reports/m6-universe-coverage.json`.
- M5 operator precompute
  - obtains product scanner IDs from the catalog initialized universe;
  - embeds `universe_coverage` provenance in its report;
  - no longer defines operator scope by globbing every local daily file.
- regression tests
  - BSE deferred;
  - delisted/orphan local files excluded;
  - listed-but-uninitialized preserved as a gap;
  - formal-QFQ is a subset;
  - operator/scanner mismatch fails;
  - deterministic hashes are stable;
  - same-exchange invalid parentage fails closed and is reported explicitly;
  - candidate_set is machine-readable but never a coverage denominator;
  - list/tuple/generator inputs produce the same deterministic universe semantics;
  - unevaluated QFQ is represented as unknown, never falsely as zero-ready.

## 7. Acceptance gates

M6.3 may close only when:

1. ISSUE-0062 is resolved by this contract;
2. all canonical layers above are machine-readable;
3. operator input equals scanner universe by invariant;
4. product reports cannot call initialized coverage full A-share coverage;
5. BSE default exclusion is explicit;
6. formal-QFQ readiness reuses the existing continuous-view semantics;
7. Project OS, Python tests, Ruff budget, Web build, browser acceptance, Phase18,
   Phase21, M4 methodology freeze and Outcome Engine freeze are green;
8. no M4 authoritative evidence is written by M6.3;
9. no harmonic identity/PRZ/lifecycle semantics change;
10. the final state/Attempt/Decision/Issue ledgers all agree.

## 8. Non-goals

M6.3 does not:

- initialize all listed A shares;
- download missing market history;
- repair QFQ factors;
- enable BSE by default;
- claim statistical significance, alpha, win rate or profitability;
- change harmonic detection or execution semantics.

Those are separate operational/research decisions and must not be smuggled into a
coverage terminology phase.
