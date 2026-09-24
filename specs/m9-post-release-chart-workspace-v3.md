# M9 post-release — Chart-centered desktop workspace v3

status: planned

## Primary workflow

- Desktop opens a single research symbol through a top command bar; Enter and Ctrl+K work.
- First launch shows a chart-centric empty workspace and recent research; reopening the app resumes the last locally initialized instrument's chart.
- Research uses a narrow icon navigation rail and chart tool rail, an expansive candlestick chart, and a right-side stock/details inspector.
- The right inspector contains an interactive local watchlist, current decision narrative, canonical crosshair context, candidate identity selector and Source Clock details.
- Select a stock in the watchlist to open its real local analysis. Save pinned symbols in browser localStorage; filter, add and remove are keyboard-accessible.
- A panel can be collapsed to enlarge the chart; tabs for pattern, market context and audit remain available without harmonic refetch.
- The selected chart shows only the latest local close and date. Other watchlist symbols show no quote until selected; no live-market claim.
- Chart pan/zoom/crosshair remain owned by Lightweight Charts and the canonical overlay. Viewport action must never request harmonic analysis.
- Keep Home, Opportunity Discovery and System Status reachable via icon navigation with text labels and keyboard focus.
- At tablet/mobile widths, stack inspector and preserve all controls without horizontal page overflow.

## Regression and closeout

Web build, browser workflow and visual inspection at desktop/mobile sizes; Project OS, full hosted browser, Phase18/21, M4 37/37 and Outcome 4/4. Record all failures and successes in Attempt Ledger. Close CR only after canonical main validation.
