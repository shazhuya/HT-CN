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
