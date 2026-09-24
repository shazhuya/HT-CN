# CR-0087 — Chart-centered desktop workspace

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 43ceed1fdf16dceb3aa746262b9566c96904b0af
target: main
milestone: M9.post_release
work_branch: m9/post-release-chart-workspace-v3

## Trigger

User acceptance feedback on Stable UX v2: the application remains difficult to operate and visually unsatisfactory. The user supplied a TradingView desktop screenshot and explicitly requests replacing the previous layout with a chart-first workspace, including a toolbar, stock list and details panel.

## Objective

Deliver a practical Windows desktop chart workspace with a compact global symbol command bar, narrow drawing/research tool rail, dominant synchronized candlestick chart, persistent watchlist and instrument details. Replace the old card-heavy Home with a chart workspace entry and recent research. Reopen the last locally initialized instrument directly on launch. Keep Chinese labels readable and make the Source lifecycle and candidate switcher reachable without a long engineering page.

## Acceptance

See `specs/m9-post-release-chart-workspace-v3.md`. Verify Web build, deterministic browser navigation/chart overlay, watchlist persistence and symbol switching, viewport interaction without recomputation, accessibility of core controls, Project OS, frozen Source/M4/Outcome gates and formal hosted CI.

## Boundaries

The screenshot is a layout reference. No TradingView branding, account widgets, unimplemented drawing tools, live quotation, or simulated price claims. Local last-close must be clearly labeled and unselected watchlist entries must not present invented prices. Preserve harmonic identity, Raw PRZ, Source Clock, M4 methodology 37/37, Outcome Engine 4/4, ISSUE-0066 claims gate, 5-0 quarantine, Alternate Bat fail-closed and no automatic trading.

## Validation and next action

Implementation underway on the named branch. The first hosted run #2770 / 35996569389 passed Python/Project OS/Web but failed 11 browser cases: 9 ambiguous old selectors for tool-rail and tabs, one new watchlist combobox selector, one missing visible API version. The screenshot showed the new chart/watchlist layout rendering. Second run #2772 / 35997215934 passed 29/31 browser cases; the remaining cases were the audit tool accessible name colliding with the old tab selector, and a request counter matching runtime status polling. Both have been corrected for the next full hosted run. Require green hosted gates before activation, merge and closeout.

Run #2774 / 35997576837 on `49d7ca1c9148221685c43c90775ec8bf92297388` passed all 31 browser cases, Phase18/21, Source Coverage, Project OS, Python/Web, M4 37/37, Outcome 4/4, release package and Stable acceptance. Artifact 10807255607 / sha256:58900fb4ae4cd63eee96f433c8713bb5d09f650485fae05d2b04b4dd17598617. Activate the change at validation_green and validate this ledger-bearing governance state before advancing to ready_to_merge.

Activated validation_green head `e3e226d5846f689546473679ca0c430723bbb54e` passed run #2776 / 35998115098, including 31/31 application browser cases, frozen Phase18/21, M4 37/37, Outcome 4/4, Stable acceptance and Project OS. Artifact 10806079871 / sha256:a6705bed536b91cc8a93fd34a18a934c7279f6bfbeb90e3fcb3198304415badc. Advance to ready_to_merge and validate that exact ledger-bearing head before merge.
