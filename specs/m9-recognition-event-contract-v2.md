# Recognition event contract v2 — CR-0090 / Gate 4C.1

status: implementing
scope: experimental Source Completion only; production promotion remains blocked

## Identity and observation clock

The source identity is (data version, adjustment basis, symbol, timeframe, detector/policy
version, family, direction, ordered XABC nodes and prices). Numeric bar indices are meaningful
only inside that data identity. A projection is born at the earliest confirmed-pivot observation
that supports its XABC, never at retrospective C time. The birth bar is available at bar close;
execution cannot be credited on that same bar. Intrabar ordering is not inferred from OHLC.

`scales` and `min_skipped_pivots` mean birth evidence. `support_events` records the first
observation per scale; use `scales_as_of(t)` to obtain only evidence known at t. Full-history
support must not score earlier births. Later support does not reset lifetime or retirement.

## State/event contract

| Event/state | Observable condition | Permitted claim |
|---|---|---|
| projection born | Confirmed XABC passes current source-cleared prefix checks | Candidate only; confluence qualification remains independently auditable |
| PRZ entry | After birth, bar range overlaps frozen Raw PRZ | Contact only, not completion or reversal |
| Terminal observed | All selected PRZ measurements have actually been covered by post-birth bar ranges, and current bullish bar overlaps PRZ and reaches its low boundary; bearish is mirrored | Directional Terminal event under this contract; no confirmed reversal claim |
| C breach | Bullish high exceeds C, or bearish low falls below C, before Terminal | Retire this frozen projection |
| unobserved far-side passage | Entire bullish bar is below PRZ, or bearish bar above PRZ, before Terminal | Operational retirement because a valid directional test was unobserved, not proof Source geometry is invalid |
| expired | No earlier retirement/Terminal by birth + lifetime_bars inclusive | Retire; default 180 bars is engineering policy, not a universal Source rule |
| reaction/reversal confirmed | Not supplied by this scanner | Never infer from Terminal; requires separate unchanged lifecycle evidence |

Priority: an earlier Terminal remains immutable despite later C/gap changes. On one bar where
C breach and Terminal could both occur, retire conservatively because OHLC cannot order them.
A Terminal at the expiry boundary is observable and wins over end-of-bar expiry; after the
boundary it cannot complete the retired projection. Retirement cannot be undone by a return
to PRZ. A genuinely new XABC has a different identity and may form independently.

Raw PRZ endpoints and touching equality are unchanged. A wide zone is not automatically
invalidated. Gap retirement is a conservative HT-CN v2 policy, not a claim quoted from Carney.
This does not reconstruct whether an actual intraday price path crossed the zone between bars.

Source checked directly: Carney Volume 3 printed pp.151-153 (PDF pages 158-160) requires
testing all PRZ numbers, potentially across consolidation bars, and distinguishes subsequent
reversal confirmation. Selected component levels and both zone boundaries require actual bar
range coverage. A jump over a level is not an observed test. Once all levels have been seen,
require a contemporaneous far-side test; do not retrospectively move completion to an older bar.
Printed p.104 (PDF111) supplies Crab ratios. The common 3-5% zone discussion on printed p.152
is descriptive relative to overall pattern range, not a universal XA-based rejection threshold.

## Explicit uncertainty

Current prefix acceptance/zone availability does not establish complete shape validity or
confluence. Label mathematical measurement consistency separately from semantic qualification.
ABCD and Shark are outside this standard-XABC implementation. No trade/win-rate claim follows.

## Acceptance status

Focused boundary tests cover birth evidence, append invariance, bullish/bearish gap-return,
retirement, expiry and same-bar ambiguity. Representative real-market labels, new sealed final
acceptance, complete data/version event IDs and application integration remain future gates.
