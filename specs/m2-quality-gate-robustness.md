# M2.9 Quality Gate Robustness

## Purpose

M2.8 identifies quality gates whose aggregate Train and Validation direction is favorable. M2.9 asks a stricter question: is that apparent improvement broad and stable, or is it driven by one stock, one period, one pattern or one pivot scale?

This stage still does **not** freeze a production quality policy and still does **not** open Holdout outcomes.

## Inputs

Only gates already declared by M2.8 are considered. M2.9 never searches arbitrary new formulas or cutoffs. Numeric cutoffs remain the Train-only quartiles/median learned by the purged chronological split.

The currently allowed signal-time evidence remains:

- canonical/source-tolerance status;
- supporting pivot-scale count;
- source pivot scale;
- PRZ width ratio;
- distance from signal close to PRZ;
- pivot confirmation lag.

## Robustness checks

A strong M2.8 gate is stress-tested in four independent ways.

### Symbol concentration

No single stock may contribute more than 30% of gated observations in either Train or Validation. This prevents one long-history or unusually volatile stock from defining the result.

### Cross-sectional direction

A stock is eligible for this diagnostic when it has at least 20 baseline observations and at least 5 gated observations inside the split.

The gate must improve both PRZ-touch rate and retirement rate direction for:

- at least 60% of eligible Train stocks;
- at least 50% of eligible Validation stocks;
- with at least 5 eligible stocks in each split.

These are HT-CN research safeguards, not Carney rules.

### Leave-one-symbol-out

The aggregate favorable direction must survive removal of every individual stock, separately in Train and Validation. This directly tests whether one instrument is carrying the result.

### Coarse time stability

Train is split into three chronological segments and Validation into two. Each eligible segment needs at least 30 baseline observations and at least 10 gated observations.

The gate must remain favorable in:

- at least two of three Train segments;
- at least one of two Validation segments.

Again, this is a research robustness diagnostic rather than an optimized trading rule.

## Candidate status

Only an M2.8 strong gate passing all four checks becomes an `robust_research_candidate`.

That label still means only:

> the quality evidence is sufficiently broad to justify further research.

It does not mean expected profit, high win rate, a trade recommendation or a frozen production rule.

## Holdout

Holdout remains sealed. M2.9 never reads Holdout outcomes. A future policy-freeze stage may choose a small fixed set of quality clauses, record their exact definitions, hash the policy, and only then open Holdout once.
