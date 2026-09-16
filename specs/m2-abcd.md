# M2 — Standalone AB=CD source contract

## Purpose

Standalone AB=CD is a **four-point A/B/C/D schema**.  It is not an XABC forming
candidate and it must not be forced into the X/A/B/C/D serializer merely to reuse UI code.
Carney describes AB=CD as the basic four-point foundation for harmonic patterns.

Primary sources:

- Scott M. Carney, *Harmonic Trading Volume One*, Chapter 4, pp. 45–46.
- Scott M. Carney, *Harmonic Trading Volume Three: Reaction vs. Reversal*, pp. 76, 80–81.

## Canonical geometry

1. Four alternating confirmed pivots are labelled **A, B, C, D**.
2. BC is a retracement of AB.
3. CD resumes the original AB direction.
4. The defining completion is the **equivalent AB=CD** relationship: `|CD| / |AB| = 1.0`.
5. C is drawn from Carney's harmonic retracement family and determines the reciprocal
   BC extension used to complement the completion area.

### Source reciprocal table

| C retracement (`|BC| / |AB|`) | reciprocal projection (`|CD| / |BC|`) |
| ---: | ---: |
| 0.382 | 2.24 **or** 2.618 |
| 0.500 | 2.0 |
| 0.618 | 1.618 |
| 0.707 | 1.414 |
| 0.786 | 1.272 |
| 0.886 | 1.13 |

Carney states that the reciprocal BC projection should converge closely with the AB=CD
completion.  For 0.382 there are two explicitly listed source alternatives; the evaluator
checks both and uses whichever actual completed geometry is closer to.

## Tolerance policy

The books allow some real-market deviation but do not define one universal numerical
percentage for every AB=CD measurement.  Therefore HT-CN does **not** write a made-up
number into the Carney rule registry.

The executable scanner currently exposes three explicit research/matching parameters:

- C reciprocal matching tolerance;
- BC reciprocal matching tolerance;
- equivalent CD/AB matching tolerance.

The current scanner default is 3% relative error for each.  This is an **HT-CN operational
matching policy**, not a claim that Carney published a 3% rule.  Tests and audit payloads
must retain that distinction.

## PRZ

Standalone AB=CD PRZ contains two auditable source-derived prices:

1. exact `AB=CD x1` completion projected from C;
2. reciprocal BC projection selected from the source table.

The displayed zone is their convergence; neither post-D reaction nor later success is
allowed to move the zone retroactively.

## Reaction vs. Reversal

Once A/B/C/D identity is frozen, the same post-completion lifecycle audit can be applied:

- Type-I 38.2% / 61.8% objectives are measured from D back toward A;
- PRZ exit/retest is descriptive post-D evidence;
- Type-II remains an evidence state requiring price/indicator confirmation;
- Wilder RSI is confirmation evidence only;
- HSI is proprietary and is not reverse-engineered or approximated by HT-CN.

## Non-negotiable anti-overfit rules

- A profitable outcome cannot promote an invalid four-point geometry to AB=CD.
- Pivot cross-scale persistence can rank audit quality but cannot change identity.
- Standalone AB=CD stays a separate schema from XABCD patterns.
- Future forming-ABC projection must be implemented as a separate three-pivot frontier;
  historical four-pivot XABC windows must never be relabelled as live ABCD projections.
