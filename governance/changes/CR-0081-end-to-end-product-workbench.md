# CR-0081 — M9.3 End-to-End Product Workbench

status: closed
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

## Formal PR validation

PR #69 run #2525 passed the complete release gate: 952 Python tests / 0 warnings, Ruff 0/0, Web build, 26 browser tests including the dedicated M9.3 end-to-end workbench scenario, Phase18, Phase21, M4 methodology frozen_match_37 and Outcome Engine frozen_match_4. Artifact: 10687973049, sha256:a57bf792a87634c03fcc93d35281a3194ffb65cceeb9733b9049dfa23cc1fc37.

## Closeout

- PR #69 merged with ancestry preserved as `1527d7c1b4f5e7840a2ac0049e1a6c76ea08f040`.
- Final ledger-bearing PR run: #2527 / workflow 35717879546, all release gates green, 26 browser tests.
- Canonical main run: #2528 / workflow 35718116527, all release gates green, 952 Python tests / 0 warnings, Ruff 0/0, Web, 26 browser tests, Phase18/21, M4 methodology 37/37 and Outcome Engine 4/4.
- Main release artifact: 10690418865 / sha256:2b7ad7724a810c4ad07bf1a8efb1248f8c4678a9641b648cba88cd31ee5cbc85.
- Continuation artifact: 10689802570 / sha256:26f8dab1f2f3204f0de3e678e5e70cedb39b9e90b90ed7035ed10f2ee7c3001c.
- No user-computer action was required.
- Next product phase: M9.4 Background Evidence, Calibration Boundary & Observability.
