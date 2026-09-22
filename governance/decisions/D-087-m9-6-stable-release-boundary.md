# D-087 — Stable v1.0.0 certifies product-runtime maturity, not statistical-performance maturity

status: active
date: 2026-09-22

## Decision

HT-CN Stable v1.0.0 is the completion boundary for the M9 product runtime. It does not assert that prospective evidence is sufficient for win-rate, Alpha, profitability, statistical significance or evidence-based calibration.

- Stable release may proceed while ISSUE-0066 is open because ISSUE-0066 is claims-only.
- While ISSUE-0066 is open, all statistical claim surfaces and M8 evidence-based calibration outputs remain explicitly unavailable.
- M7 continues prospective evidence accumulation in the background after Stable v1.0.0.
- Stable release requires automated market data, automated harmonic runtime, integrated workbench, background evidence, reliability/recovery, zero-CLI operation, verified release identity and formal release gates.
- Version identity is singular: Python package, API, Stable Product Contract and release manifest must all report 1.0.0.
- Formal release artifacts must include the verified release ZIP and stable acceptance report.
- The stable release package must contain the Stable Product Contract, Operator Runbook, Recovery Contract and v1.0.0 Release Notes.
- Automatic trading remains disabled.
- FIVE_ZERO remains quarantined, Alternate Bat remains fail-closed and HSI remains unsupported.
- Stable release does not mutate Source identity, Source Raw PRZ, lifecycle, frozen M4 methodology or the frozen Outcome Engine.

## Failure boundary

Version drift, missing stable documents, an unverified package, a packaged runtime that requires Git, failed package 37/4 guards, enabled statistical claim surfaces, automatic trading, or any formal release-gate failure blocks Stable release.

## Post-release boundary

Product maintenance may continue after M9 closes. M7/M8 research progress may add authorized empirical capabilities later, but it must not retroactively redefine the v1.0.0 frozen Source and evidence boundaries.
