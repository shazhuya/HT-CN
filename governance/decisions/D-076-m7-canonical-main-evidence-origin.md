# D-076 — M7 prospective evidence originates only from current canonical main

status: `active`

## Decision

Starting with M7, the one-click prospective evidence workflow must fail closed unless the local
checkout is a clean `main` whose `HEAD` exactly matches a freshly fetched `origin/main`.

The former operational dependency on the historical
`m4/real-a-share-validation-workflow` branch is retired for new M7 captures.

## Rationale

The capture methodology and Outcome Engine are already frozen by exact component guards. Continuing
to require an old development branch would split project authority: Project OS would say canonical
`main`, while real evidence collection would still originate from a historical branch.

Canonical-main identity plus the existing freeze guards gives one auditable origin without changing
the frozen research semantics.

## Boundaries

- This decision changes only the operational preflight/wrapper.
- It does not change any of the 37 frozen M4 methodology components.
- It does not change any of the 4 frozen Outcome Engine components.
- Existing committed evidence is not rewritten.
- The M7 accumulation status report is derived, non-authoritative, and cannot authorize win-rate,
  alpha, profitability, significance, or trading claims.
- ISSUE-0066 remains the gate for future statistical conclusions.
