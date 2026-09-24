# CR-0088 — Harmonic recognition recall and persistent discovery layer

status: implementing
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
