# D-070 — Immutable M4 components are governed by freeze guards, not lint rewrites

status: `active`

## Decision

M4 capture-methodology and Outcome Engine frozen component files must remain byte-identical to
their authoritative freeze lineage. Repository quality cleanup must not rewrite those files merely
to satisfy a later linter version or style rule.

The exact frozen paths are therefore listed in Ruff per-file ignores. This is an explicit governance
boundary, not a claim that those historical files are lint-clean.

- M4 capture methodology remains protected by the 37-component freeze guard.
- Outcome Engine remains protected by the 4-component freeze guard.
- Any byte change to a frozen component continues to fail the corresponding freeze guard.
- All non-frozen / mutable Python code remains subject to the repository Ruff gate and M6.4 targets
  zero observed mutable-code violations.

## Rationale

Ruff safe autofix demonstrated that syntax-safe lint rewrites can still change bytes in frozen
methodology files. For HT-CN, the frozen Source/research identity is a stronger invariant than
style modernization. Mixing the two would make a repository-governance cleanup mutate the very
methodology it is required to preserve.

## Prohibitions

- no bulk `--unsafe-fixes` on frozen or mutable code;
- no lint-only edit to a frozen M4 component;
- no statement that per-file ignored frozen components are Ruff-clean;
- no weakening of the 37/37 or 4/4 freeze guards.

## M6.4 quality meaning

A final Ruff count of zero means zero violations in the mutable lint-governed scope, with the
immutable freeze paths explicitly excluded and independently required to pass their byte-level
freeze guards.
