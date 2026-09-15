# M2.5 — Reaction vs. Reversal audit semantics

## Source authority

Primary authority: Scott M. Carney, *Harmonic Trading Volume Three: Reaction vs. Reversal*.

The implementation intentionally separates three things:

1. **Pattern identity** — XABCD geometry and PRZ. No future bars may change whether a historical candidate was a valid Carney identity at D.
2. **Post-D outcome audit** — descriptive observations after D: 38.2% / 61.8% reaction targets, PRZ exit, and later PRZ retest.
3. **Trading/market context** — not part of M2 geometry and not allowed to rewrite identity.

## Type-I descriptive audit

For a completed XABCD pattern, the automatic reaction objectives are measured from D back toward A using the A-D span:

- T1 = 38.2%
- T2 = 61.8%

Bullish completion: targets project upward from D toward A.
Bearish completion: targets project downward from D toward A.

The audit records the first bar after D that touches each objective. It also records whether the first 3 and first 5 post-D bars avoid re-entering the original PRZ, because Volume Three emphasizes demonstrative counter-trend behavior within roughly 3–5 bars.

These observations are **not** converted into a win probability or a trade recommendation.

## Type-II candidate semantics

Volume Three describes Type-II as a secondary test/re-entry of the original PRZ after the initial Type-I event and requires additional price/indicator confirmation.

HT-CN therefore uses the conservative label `type_ii_candidate` only when:

1. price first exits the original PRZ in the reversal direction; and
2. later price re-enters/overlaps the original PRZ.

This is deliberately **not** called a valid Type-II reversal. RSI/HSI/price-trigger confirmation is a later layer and must be implemented separately before a stronger label is permitted.

## No look-ahead contamination

Post-D bars are used only by `audit_completed_reaction`. They never feed back into Pivot selection, XABCD identity, ratio checks, PRZ construction, or geometry score.

## Automated evidence

`运行M2综合验收.bat` now produces, without manual screenshots:

- deterministic Python/Web/API/browser QA;
- local QFQ harmonic scan;
- `artifacts/reports/m2-reaction-audit.json`;
- `artifacts/golden_candidates/manifest.json` with real local A-share review candidates;
- local database health audit.

Golden candidates are explicitly marked `candidate_not_certified`. Promotion to a real Golden Case requires independent audit of pivot choice, geometry, PRZ, and post-D path.
