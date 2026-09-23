# D-087 — M9.6 Stable release acceptance composes existing product gates; it does not create new research truth

status: active

## Decision

M9.6 is a composite product-release gate over M9.1-M9.5. It may close M9 while ISSUE-0066 remains open because ISSUE-0066 gates only statistical/alpha/profitability/evidence-calibration claims.

The Stable Product release identity is bound by:

- the existing deterministic M9.5 release package and `HTCN_RELEASE_IDENTITY.json`;
- `pyproject.toml` project version;
- `governance/STABLE_RELEASE.json`;
- a formal `m9-stable-release-acceptance.json` produced after browser and freeze gates.

Operator and recovery documentation are release payload, not chat-only instructions.

## Permanent constraints

1. M9.6 must not redefine Source identity, Raw PRZ, Source Clock, Reaction/Reversal, M4 methodology or Outcome Engine semantics.
2. Stable Product acceptance does not authorize win-rate, Alpha, profitability, statistical-significance or evidence-based calibration claims.
3. M7 continues as background evidence after product release; M8 remains fail-closed until an explicit future authorization exists.
4. Normal product operation remains zero-CLI and does not require daily ZIP handoff or AI manual acceptance.
5. User-computer execution remains exceptional under Product Completion Policy; M9.6 acceptance itself is hosted/fixture/package-verification work.
6. HT-CN remains an artificial decision-support/research system and does not execute securities trades.
