# D-088 — Stable UI defaults to human workflow; engineering detail uses progressive disclosure

status: active
date: 2026-09-23

## Decision

HT-CN's Stable product UI must optimize the default viewport for a human research workflow, not for exposing the internal project architecture.

The default product hierarchy is:

1. global runtime/data health;
2. instrument selection and primary action;
3. chart and current pattern state;
4. "现在在哪 / 先看什么 / 下一关键条件" decision narrative;
5. candidate selection and key harmonic levels;
6. secondary market/context information;
7. audit, evidence, history and governance detail behind explicit disclosure.

## Interaction rules

- The chart is the primary workspace, not a secondary card below queues and diagnostics.
- The user must be able to select an instrument and trigger analysis from a visually dominant command surface.
- Existing operator queue, history, daily review, context integrity and evidence capabilities remain accessible, but they must not force the user through a long page before reaching the single-instrument workspace.
- Technical terms may remain where fidelity requires them, but the first visible label should be understandable in ordinary Chinese.
- Product health should summarize normal/degraded/blocked states without requiring the operator to read raw process names.
- Progressive disclosure must not remove auditability; it only changes information priority.
- Presentation state may not own or mutate harmonic identity, Source Raw PRZ, lifecycle, M4 evidence or Outcome semantics.
- Viewport changes remain presentation-only and must never trigger harmonic recomputation.

## Validation boundary

Browser tests must prove the primary human journey remains functional: load product -> see status -> select/search instrument -> analyze -> view chart -> read current state and next observation -> open secondary detail when needed.
