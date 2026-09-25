# CR-0088 — Harmonic recognition recall and persistent discovery layer

status: validation_green
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: b412ffd8eb5e82416b46a8235fc9d6d68702a858
target: main
milestone: M9.post_release
work_branch: m9/post-release-recognition-recall-v1

## Trigger

Direct user acceptance defect: Stable HT-CN renders very few or no useful harmonic structures on charts where the standalone TradingView Pine project finds multiple visually meaningful structures. Code audit identifies systematic low recall caused by frontier-only XABC discovery, consecutive-pivot-only candidate construction, small default pivot scales, and strict canonical identity gates being used too early as discovery gates.

## Objective

Add a high-recall, deterministic, non-authoritative harmonic discovery channel that:
- discovers persistent XABC projections before exact completed identity exists;
- evaluates multiple recent swing paths instead of only consecutive pivot windows;
- uses product discovery scales aligned with the proven Pine baseline (5/10/20) without replacing authoritative source scales;
- keeps broad source structural envelopes as discovery gates while exposing discrete harmonic-family alignment as quality metadata rather than deleting the candidate;
- reconstructs PRZ test status only from bars observable after C confirmation;
- gives the product a useful candidate list and chart overlays even when the authoritative completed/forming channel is empty.

## Non-goals / freezes

Do not modify Source Raw PRZ definitions, CARNEY_RULES canonical identity, M4 frozen methodology, Outcome Engine, Source Clock semantics, 5-0 quarantine, Alternate Bat fail-closed, HSI unsupported state, or automatic-trading prohibition. Discovery candidates cannot write M4 evidence, cannot become authoritative Source identity by score, and cannot fabricate D.

## Acceptance

See `specs/m9-post-release-recognition-recall-v1.md`. Require deterministic Python tests for graph/path discovery, persistence, no-lookahead PRZ testing and strict-channel separation; API contract tests; browser tests proving discovery candidates render and are visibly labelled; full Project OS / Source Coverage / Python / Web / browser / Phase18 / Phase21 / M4 37/37 / Outcome 4/4 / Stable gates in hosted CI.

## Absorbed prior CR-0088 audit evidence

The earlier research-only branch `m9/recognition-recall-audit` / draft PR #78 is incorporated as evidence, not as a competing implementation. It replayed two overlapping real 688256 **daily** OHLC datasets and found:

- 140-bar sample: production S3/5/8/13 produced zero standard XABCD completed and zero current XABCD forming; raw/adjusted bases were audited separately.
- 244-bar sample: production S3/5/8/13 again produced zero standard completed and zero current forming XABCD; diagnostic S2 exposed three historical strict XABC windows, none current.
- On the 140-bar raw sample, 40 historical XABC windows yielded 18 B-band pairs, 5 B+C structural-band pairs, and 0 candidates surviving the operational C-family ±3% gate. The closest non-quarantined case was a Butterfly prefix with C/AB≈0.848, about 4.3% from 0.886.
- A source-shaped exact Gartley completed fixture accepts exact D/XA=0.786 while a 0.01 price-unit D movement can reject canonical completion. This demonstrates why a nearby/discovery channel must remain separate from authoritative identity rather than relaxing Source identity by score.
- The user's TradingView comparison screenshot is **1-hour**, while the audited repository product path is daily. Exact hourly Pine parity remains unverified until full same-timeframe OHLC and price-basis settings are available. This implementation must not claim that daily evidence proves hourly parity.

This Change therefore repairs the product's discovery/existence gate now, while retaining same-timeframe Pine parity as an explicit follow-up acceptance boundary rather than fabricating evidence.

## Validation and next action

Planned PR #79 head `ede373cf1af0ebd25418b87af655dbc5aa888590` passed hosted run #2866 / 36084996916: Project OS, Source Coverage, zero-debt Ruff, Python/API, Web, discovery and legacy Stable browser acceptance, Phase18/21, M4 methodology 37/37, Outcome Engine 4/4, M9.5 release package and M9.6 Stable acceptance. Release artifact 10843815303, digest `sha256:7afa81b05caaa309db249b2acc6bb8f96c2eb0ce2bbb51a6dad0ee3e736ecaaa`.

The implementation is now activated at `validation_green`. Validate this exact ledger-bearing governance state before advancing to `ready_to_merge`. This green result establishes the product-functional discovery repair, not exact 1-hour TradingView Pine parity; matched hourly OHLC / price basis / pivot settings remain a separate evidence boundary.
