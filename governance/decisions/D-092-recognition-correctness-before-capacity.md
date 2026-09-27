# D-092 — Recognition semantics and independent acceptance precede capacity selection

status: active
date: 2026-09-27

Under D-091 and explicit user authorization, adopt
`specs/m9-recognition-gate4c-correctness-first.md` as the current CR-0090 execution order.
This supplements D-091; it does not supersede its highest-priority status.

1. Gate 4B engineering green does not establish semantic recognition reliability.
2. Resolve event semantics and PRZ confluence evidence before graph-capacity selection.
3. Require representative labelled validation and a fresh sealed final test. A holdout used to
   choose parameters is validation, even if individual case details were hidden.
4. Only after correctness acceptance may V2 enter the product via one versioned interface.
5. Keep peripheral development frozen and Source/M4/Outcome boundaries intact. Verified Source
   defects require a new explicit Source Decision and versioned migration, never silent edits.
6. No time-wait, user-PC routine or repeated unrelated full-suite work substitutes for case resolution.

Evidence and limitations: `governance/reviews/2026-09-27-recognition-architecture-audit.md`.
No detector improvement or production readiness is claimed by this planning decision.

## 2026-09-27 用户方向复核补充

按执行规范末节落实案例到引擎修复的闭环；治理工作不得替代识别改进。
局部 Source 争议不得演变成全项目停摆；未裁定能力保持不通过。
全拒绝或永久 unverified 不构成可靠识别，必须同时控制漏检与误检。
此次补充不修改 Source 规则，不宣称新的识别成绩。
