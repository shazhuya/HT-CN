# M2 — Shark / 5-0 source contract

## Purpose

Shark and 5-0 are **not** standard M/W XABCD identities. HT-CN gives them dedicated
schemas, evaluators, Source Raw PRZ contracts and forming projectors so their segment
semantics cannot be silently coerced into Gartley/Bat/Crab logic.

Primary sources:

- Scott M. Carney, *Harmonic Trading Volume Two*, 5-0 chapter (Basic 5-0 Requirements).
- Scott M. Carney, *Harmonic Trading Volume Three: Reaction vs. Reversal*, Shark pp.116–129 and 5-0 pp.129–138.

## Shark — `0-X-A-B-C`

Volume Three freezes the following structural measurements:

1. `A/0X = 0.382–0.618`.
2. `B/XA = 1.13–1.618`.
3. The Extreme Harmonic Impulse into C is `C/AB = 1.618–2.24`.
4. The completion retest is `C/0B = 0.886–1.13`.
5. `0.886 0B` is the minimum completion retest, `1.0 0B` is a common focus, and
   `1.13 0B` is the maximum completion / stop-limit reference.
6. The 0B completion corridor and AB Extreme Harmonic Impulse corridor must align.

### Shark Source Raw PRZ — M2.30 freeze

The book does not define Shark completion as one synthetic midpoint. It describes a
preferred completion **alignment** between two published source corridors. HT-CN therefore
freezes Shark Source Raw PRZ as the geometric overlap of:

- `0B 0.886–1.13 completion corridor`; and
- `AB impulse 1.618–2.24 completion corridor`.

If those published corridors do not overlap for the signal-visible `0-X-A-B` geometry,
Source Raw PRZ is unresolved and the candidate fails closed for source-aligned execution.
The generic `ideal_core` engineering alias cannot substitute for the Source Raw PRZ.

The `1.13 0B` price remains the outer source completion / stop reference. It is not a
reaction target and is not a generic XABCD stop formula.

A live forming Shark is the **latest confirmed 0-X-A-B frontier**. Historical four-pivot
slices cannot remain permanently “forming” after a later confirmed pivot exists.

### Shark reaction management

Shark is explicitly reactionary. Volume Three links management to the prospective 5-0:

- 50% retracement of the B-to-C/Terminal completion leg;
- Reciprocal AB=CD projected from C/Terminal;
- 61.8% as the wider prospective 5-0 management level.

The Shark **initial target** is the lesser reaction distance / first encountered of the
50% level and Reciprocal AB=CD. If 50% is encountered first, 61.8% remains the wider
follow-on 5-0 level. These measurements are post-completion management evidence only:
**none of them belongs to Shark identity or Shark Source Raw PRZ.**

For source-aligned research, C is represented by the observed Shark Terminal Price Bar
extreme, not by a later right-confirmed retrospective pivot.

## 5-0 — `X-A-B-C-D`

Volume Two defines the structural five-point contract:

1. `B/XA = 1.13–1.618`.
2. `C/AB = 1.618–2.24`; failure to reach 1.618 invalidates the 5-0.
3. Structural D completion uses the **50% BC retracement** and the Reciprocal AB=CD.
4. Reciprocal AB=CD is the complementary source measurement, not a requirement to fit
   inside a synthetic 50–61.8 band.

### 5-0 Source Raw PRZ — M2.29 freeze

The Source Raw PRZ has exactly these two structural members:

- `50% BC structural completion`;
- `Reciprocal AB=CD`.

The Raw PRZ spans/alines those two source measurements. There is **no universal rule** that
the Reciprocal AB=CD must lie inside a 50–61.8 interval in order for 5-0 identity to exist.
The earlier HT-CN implementation that compressed 5-0 into a universal `50–61.8` identity
band is superseded and must not be reintroduced.

### Volume Three 61.8 execution refinement

Volume Three adds a 61.8 make-or-break / stop refinement around 5-0 execution. Its prose
and PRZ figures contain inconsistent XA/AB labels while the structural figures and market
examples retain the B-C pullback geometry. HT-CN therefore:

- preserves Volume Two `50% BC + Reciprocal AB=CD` as Source Raw PRZ membership;
- keeps 61.8 **outside identity and outside Source Raw PRZ**;
- records 61.8 only as an explicit execution/stop refinement under the current BC-axis
  engineering interpretation;
- keeps the Volume Three label conflict visible rather than rewriting it into a source claim.

Production 5-0 remains quarantined until that source-label conflict is resolved strongly
enough for production semantics. Research can opt in to the reconciled structural contract.

A live forming 5-0 is the **latest X-A-B-C frontier** after B/XA and C/AB satisfy source
geometry. It must not be rejected merely because Reciprocal AB=CD lies before the 50% level.

### 5-0 reaction targets

For source-aligned Type-I research, automatic 38.2% / 61.8% reaction targets are measured
from the **C-to-Terminal completion leg**. Standard XABCD A-to-Terminal target semantics
must not be reused for 5-0.

## Separation from generic XABCD

`CARNEY_RULES[*].executable_identity=False` for Shark and 5-0 means only that the generic
standard XABCD evaluator must not execute those registry rows. Dedicated modules own their
source contracts.

- standard M/W XABCD evaluator: Gartley, Bat, Alternate Bat, Butterfly, Crab, Deep Crab;
- standalone `ABCD` evaluator: four-point AB=CD;
- dedicated `0XABC` evaluator: Shark;
- dedicated `FIVE_ZERO` evaluator: 5-0.

## Anti-overfit / governance rules

- Future price action cannot promote invalid geometry into valid identity.
- Source Raw PRZ must be rebuilt from signal-visible geometry; later pivots cannot rewrite it.
- Cross-scale support and geometry score can rank candidates but cannot rewrite source ratios.
- No HSI formula is inferred or approximated. HSI remains proprietary.
- No universal tolerance is attributed to Carney where the source does not publish one.
- Shark reaction targets and 5-0 lifecycle evidence remain separate from identity.
- Historical research versions remain frozen; M2.29 created v5 and M2.30 creates v6 rather
  than relabelling or recomputing prior closed results.
