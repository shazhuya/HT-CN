# D-089 — Stable product uses destination-based application navigation, not a long-page document

status: active
date: 2026-09-23

## Decision

HT-CN Stable will use an application-shell information architecture with explicit destinations rather than rendering all capabilities in one vertically stacked page.

Primary destinations are:
- 首页
- 个股研究
- 机会发现
- 系统状态

The research destination owns instrument-specific work. Candidate discovery owns universe scanning. Runtime and evidence diagnostics live under system status. Advanced research information uses in-workspace tabs rather than forcing the operator to scroll through unrelated sections.

## Rationale

A technically complete single-page interface can still be operationally unusable because it requires users to mentally parse implementation categories, remember vertical positions, and repeatedly scan irrelevant information. Application navigation should reflect user goals, not repository/module boundaries.

## Boundaries

Navigation and presentation state may never own or mutate harmonic identity, Source Raw PRZ, Source clock/lifecycle, M4 evidence, Outcome semantics, or calibration authority. View changes and tabs remain presentation-only.
