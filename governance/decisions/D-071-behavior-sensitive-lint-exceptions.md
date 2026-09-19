# D-071 — Behavior-sensitive legacy lint is exception-ledgered, not silently rewritten

status: `active`

## Decision

M6.4 distinguishes mechanical lint debt from rules whose automatic remediation can change runtime,
failure, calendar, API or fixture semantics.

The exact legacy exceptions are machine-readable in
`governance/QUALITY_EXCEPTIONS.json` and mirrored as exact-path/exact-rule Ruff per-file ignores.

No wildcard exception is allowed. A new exception requires an explicit Change record.

The initial behavior-sensitive rule families are:

- `BLE001`: orchestration/provider/evidence boundaries that intentionally normalize unpredictable
  external/process/filesystem/provider failures;
- `TRY004`: existing malformed-payload validator exception contracts;
- `DTZ011` / `DTZ001`: existing date-only market-calendar or legacy fixture semantics;
- `S110`: intentional provider failover suppression;
- `B008`: FastAPI dependency/body metadata declarations;
- `B017`: an existing broad negative-path test contract;
- `RUF012`: existing test-stub state semantics.

## Guardrails

1. This is not a global Ruff ignore list.
2. Every exception is bound to an exact file and exact rule.
3. Other Ruff rules remain active in those files.
4. New files receive no inheritance from these exceptions.
5. M6.4 still requires all non-exception, non-frozen mutable lint findings to reach zero.
6. Any later semantic cleanup of these exceptions requires dedicated tests and a separate Change.
