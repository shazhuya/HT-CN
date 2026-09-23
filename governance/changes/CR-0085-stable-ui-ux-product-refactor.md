# CR-0085 — Stable UI/UX Product Refactor

status: implementing
baseline_ref: main
baseline_head: c41243102c60bbde62be35c69b6d23e913f5dbf5
target: main
milestone: M9.post_release
work_branch: m9/post-release-ui-ux-v1

## Trigger

The Stable v1.0.0 runtime is technically complete but the released UI is not usable enough for real human daily research. The current page exposes too many engineering/research internals at once, lacks a clear visual hierarchy, and requires the operator to understand HT-CN implementation concepts before knowing where to look or what to do.

This change is driven by direct user feedback that the formal release has essentially no practical usability and needs a full UI/UX rethink, not cosmetic patching.

## Objective

Turn HT-CN from an engineering-style acceptance page into a polished, human-centered A-share research workstation whose default screen answers, in order:

1. Is the product/data runtime healthy?
2. What instrument am I looking at?
3. What is the current market/pattern state?
4. Where is price now relative to the harmonic structure?
5. What should I inspect first?
6. What is the next key condition/price?
7. What information is secondary and can stay out of the way?

## Product principles

- Chinese-first, plain-language first; internal milestone names and governance details are secondary.
- Primary workflow first; audit/evidence/history remain available but do not dominate the default viewport.
- Chart is the visual center of gravity.
- Search/select/analyze must be obvious and low-friction.
- Current state and next observation must be visually prominent.
- Progressive disclosure replaces long engineering pages.
- Status uses concise, human-readable labels; raw technical diagnostics are secondary.
- Desktop-first for Windows 11, but responsive behavior must remain functional.
- Visual polish must include spacing, typography, contrast, states, hover/focus, density and empty/loading/error experiences.
- Accessibility basics: semantic controls, visible focus, useful labels, sufficient contrast and keyboard-friendly primary actions.

## Scope

- application shell and navigation;
- top global status bar;
- instrument command/search area;
- operator queue presentation;
- chart-centered analysis workspace;
- right-side current-state / next-step decision rail;
- progressive disclosure for audit/context/evidence/history;
- design tokens and consistent component styling;
- responsive desktop/tablet/mobile layout;
- loading, empty, degraded and blocked states;
- browser regression for the new primary journey.

## Non-goals / fixed boundaries

- no change to harmonic identity, ratios, Source Raw PRZ, Source Clock or lifecycle ownership;
- no mutation of M4 methodology or Outcome Engine;
- no enablement of statistical claims while ISSUE-0066 is open;
- no automatic trading;
- no fabricated price/action recommendation;
- no viewport-triggered harmonic recomputation;
- 5-0 remains quarantined, Alternate Bat fail-closed, HSI unsupported.

## Acceptance

See `specs/m9-post-release-ui-ux-v1.md`.

## Validation / closeout

All meaningful implementation, browser validation, CI failures, fixes, merge and post-merge checks must be appended to the Attempt Ledger before closeout.
