# M2 — Shark / 5-0 source contract

## Purpose

Shark and 5-0 are **not** standard M/W XABCD identities. HT-CN gives them dedicated
schemas, evaluators and forming projectors so their segment semantics cannot be silently
coerced into Gartley/Bat/Crab logic.

Primary sources:

- Scott M. Carney, *Harmonic Trading Volume Two*, 5-0 chapter (Basic 5-0 Requirements).
- Scott M. Carney, *Harmonic Trading Volume Three: Reaction vs. Reversal*, Shark pp.116–129 and 5-0 pp.129–136.

## Shark — `0-X-A-B-C`

Volume Three’s figure-level specification freezes these measurements:

1. `A/0X = 0.382–0.618`.
2. `B/XA = 1.13–1.618`.
3. The Extreme Harmonic Impulse into C is `C/AB = 1.618–2.24`.
4. The completion retest is `C/0B = 0.886–1.13`.
5. The 0B and AB completion ranges must converge; the 1.13 0B extension is the outer
   source limit, not a generic XABCD stop rule.

A live forming Shark is therefore the **latest confirmed 0-X-A-B frontier**. Historical
four-pivot slices cannot remain permanently “forming” after a later confirmed pivot exists.

### Shark reaction targets

Shark is explicitly reactionary. Volume Three links its management to the coming 5-0 PRZ:

- 50% BC retracement;
- 61.8% BC retracement as the wider 5-0 area;
- Reciprocal AB=CD from C.

HT-CN records these targets and the number of bars required to touch them. They are
post-completion outcome evidence and cannot alter Shark identity retroactively.

## 5-0 — `X-A-B-C-D`

Volume Two defines the core five-point structure:

1. `B/XA = 1.13–1.618`.
2. `C/AB = 1.618–2.24`; failure to reach 1.618 invalidates the 5-0.
3. D is defined by the **50% BC retracement** together with the Reciprocal AB=CD.
4. Reciprocal AB=CD is an equivalent AB-length projection from C and must converge with
   the completion area.

Volume Three does not discard those rules. It refines execution and make-or-break handling
by incorporating the **61.8% BC retracement**. HT-CN therefore preserves the source tension
explicitly instead of pretending the books state one identical number:

- 50% remains the Volume Two defining completion;
- 50–61.8% is the Volume Three refined execution band;
- the Reciprocal AB=CD projection must lie inside that band for an executable HT-CN 5-0;
- completed candidates record whether D is closer to the original 50% completion or the
  later 61.8% refinement.

A live forming 5-0 is the **latest X-A-B-C frontier** after B/XA and C/AB already satisfy
source geometry and the projected Reciprocal AB=CD converges inside the 50–61.8% band.

## Separation from generic XABCD

`CARNEY_RULES[*].executable_identity=False` for Shark and 5-0 means only that the generic
standard XABCD evaluator must not execute those registry rows. Both schemas are executable
through their dedicated modules.

This distinction is deliberate:

- standard M/W XABCD evaluator: Gartley, Bat, Alternate Bat, Butterfly, Crab, Deep Crab;
- standalone `ABCD` evaluator: four-point AB=CD;
- dedicated `0XABC` evaluator: Shark;
- dedicated `FIVE_ZERO` evaluator: 5-0.

## Anti-overfit rules

- Future price action cannot promote invalid geometry into a valid identity.
- Cross-scale pivot support ranks structural robustness only; it cannot rewrite ratios.
- No HSI formula is inferred or approximated. HSI remains proprietary.
- No universal tolerance is attributed to Carney where the source does not publish one.
- Shark reaction targets and 5-0 lifecycle evidence remain separate from identity.
