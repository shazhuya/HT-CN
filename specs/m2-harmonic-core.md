# M2 Harmonic Core

## 1. Authority and non-negotiable separation

M2 is a clean harmonic-engine layer. Its authoritative geometry sources are Scott M. Carney:

1. *Harmonic Trading: Volume One*
2. *Harmonic Trading: Volume Two*
3. *Harmonic Trading Volume 3: Reaction vs. Reversal*

A-share market logic may rank, filter, or manage a Carney-valid candidate, but it MUST NOT mutate Carney pattern identity geometry. Code therefore separates:

- `identity`: pattern geometry and Fibonacci relationships;
- `quality`: symmetry, convergence, completion quality, pivot quality;
- `context`: A-share liquidity, board limits, market regime, gap/limit behavior, etc.;
- `management`: reaction/reversal confirmation, stop/target handling.

## 2. M2 pipeline

```text
continuous adjusted OHLC
    -> multi-scale pivots / swing graph
    -> candidate node sequences
    -> ratio measurement
    -> pattern identity validator
    -> PRZ components + convergence
    -> forming/completed state
    -> quality score
    -> A-share context layer (later)
```

Identity must never depend on UI state or drawing state.

## 3. Source-verified initial rules

The first registry freezes only ratios directly verified in the three volumes. Later commits may refine a rule, but any source conflict must be represented explicitly instead of silently choosing one interpretation.

### AB=CD reciprocal ratios

Volume One Ch.4 and Volume Three repeat the reciprocal table:

| C/AB retracement | BC projection |
|---:|---:|
| 0.382 | 2.24 / 2.618 (V3 also discusses larger layering possibilities) |
| 0.500 | 2.000 |
| 0.618 | 1.618 |
| 0.707 | 1.414 |
| 0.786 | 1.272 |
| 0.886 | 1.130 |

### XABCD families (Volume Three pattern specification chapter)

- Gartley: B=0.618 with ±0.03 absolute tolerance; AB=CD to 1.27 AB=CD; BC=1.13–1.618; D/XA=0.786.
- Bat: B=0.382–0.50; AB=CD to 1.618 AB=CD; BC=1.618–2.618; D/XA=0.886. V3 separately notes 0.50 B alignment with ±0.05 maximum tolerance.
- Alternate Bat: B <= 0.382 (V3: max with 0.03 tolerance); 1.618 AB=CD; BC=2.0–3.618; D/XA zone=0.886–1.13.
- Butterfly: B=0.786 with ±0.03 absolute tolerance; AB=CD to 1.27 AB=CD; BC=1.618–2.24; D/XA=1.27.
- Crab: B=0.382–0.618; AB=CD to 1.618 AB=CD; BC=2.618–3.618; D/XA=1.618.
- Deep Crab: B=0.886 minimum with +0.05 tolerance; AB=CD to 1.618 AB=CD; BC=2.0–3.618; D/XA=1.618.

### Shark

Volume Three advanced specification:

- schema is `0XABC`, not XABCD;
- A point retraces 0X by 0.382–0.618;
- Extreme Harmonic Impulse must be at least 1.618 and no more than 2.24;
- completion must test at least 0.886 of 0B;
- 1.13 of 0B is the maximum structural limit;
- Shark is reaction-oriented and is a precursor to the 5-0.

### 5-0

Volume Two defines the original structure; Volume Three refines management language.

- non-M/W structure;
- extreme impulse at C: 1.618–2.24;
- Reciprocal AB=CD is required;
- Volume Two describes the PRZ with the 50% BC retracement plus Reciprocal AB=CD;
- Volume Three discusses the 50% completion level together with 61.8% as the make-or-break/stop boundary and uses XA wording in parts of the chapter.

Because the two books use segment wording that must be reconciled against diagrams/cases, the 5-0 registry remains `source_conflict=true` and its executable identity validator stays disabled until the figure-level audit is complete.

## 4. Engineering invariants

1. Pattern identity is evaluated on immutable point sequences.
2. Node labels are semantic (`X/A/B/C/D`, `0/X/A/B/C`) and never derived from screen coordinates.
3. Forming patterns and completed patterns are different states, never the same candidate with a cosmetic flag.
4. A candidate can fail identity without being deleted; rejection reasons are retained for audit/debug.
5. A pattern can be geometrically valid yet low-quality. Identity and quality are separate outputs.
6. Price adjustment must be continuous before pivots are generated; raw unadjusted bars remain preserved by M1.
7. Tolerances are explicit data, not hidden `if` constants inside validators.
8. Source conflicts block automation for that rule instead of being guessed.

## 5. M2 delivery sequence

- M2.1: ratio primitives + source registry + immutable point models.
- M2.2: multi-scale pivot/swing graph with deterministic tests.
- M2.3: XABCD candidate generation and identity validation.
- M2.4: PRZ composition/convergence and forming vs completed lifecycle.
- M2.5: Shark/5-0 special schemas after figure-level reconciliation.
- M2.6: golden cases, negative cases, regression corpus, API payloads.
- M2.7: chart rendering and agent screenshot QA.

The user-facing UI remains Chinese-first; technical identifiers may remain English for code stability.