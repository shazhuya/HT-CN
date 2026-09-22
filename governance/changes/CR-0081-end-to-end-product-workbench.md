# CR-0081 — M9.3 End-to-End Product Workbench

status: implementing
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 1d779e00a25cea4820783d83c150b69c2deee72f
target: main
milestone: M9.3
work_branch: m9/end-to-end-product-workbench-v1

## Objective

Turn the already-integrated M3/M5/M6.6/M9.1/M9.2 capabilities into one coherent daily product workflow rather than a collection of separate research panels.

## Scope

- surface M9.1 market-data and M9.2 harmonic-runtime readiness directly in the workbench;
- make symbol selection and Operator Queue selection flow directly into single-instrument deep analysis;
- keep canonical candlesticks, harmonic geometry, ratios, Source Raw PRZ/PEZ, targets and lifecycle in one visible workspace;
- share chart crosshair canonical bar/node/lifecycle identity with the information panel;
- keep the existing Chinese decision narrative visible beside the live research context;
- add deterministic browser acceptance for the complete user workflow.

## Fixed boundaries

- no Carney identity, ratio, pivot, Raw PRZ, Terminal Price Bar, PEZ, Type-I or Type-II semantic changes;
- no predictive score, win-rate, alpha or profitability claims;
- no trading execution;
- viewport/crosshair/pattern selection are presentation state and must not trigger harmonic identity recomputation;
- no fabricated future nodes;
- M4 authoritative evidence remains untouched;
- ISSUE-0066 remains claims-only and non-blocking;
- no routine user-computer dependency.

## Acceptance

See specs/m9-phase-3-end-to-end-product-workbench.md.
