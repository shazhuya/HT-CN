# D-074 — Source Coverage Freeze uses a finite capability taxonomy and machine bindings

status: `active`

## Decision

M6.5 freezes the three-book Source capability surface in `governance/SOURCE_COVERAGE.json`.

Every capability is classified as exactly one of:

- `supported`
- `partial`
- `quarantined`
- `unsupported`

No current capability is classified `partial`. Partial must not be invented to blur a Source
conflict or unfinished implementation.

Every supported or quarantined capability must bind Source evidence, spec, code, tests and
Decision records. Unsupported capabilities must bind Source/spec/Decision evidence but must not
claim runtime code/tests as implementation proof.

## Frozen critical states

- Standard Gartley/Bat/Crab/Deep Crab/Butterfly, standalone AB=CD and Shark: supported.
- Shark topology: 0-X-A-B-C; never fabricate D.
- 5-0: quarantined.
- Alternate Bat: quarantined with production `fail_closed`.
- RSI BAMM core state machine/confluence: supported confirmation/execution evidence only.
- RSI BAMM Acceleration Trigger: unsupported/deferred.
- Terminal Price Bar, PEZ, Type-I, Type-II and Reaction-vs-Reversal taxonomy: supported.
- HSI: unsupported.
- Source Raw PRZ remains distinct from engineering display/execution layers.

Any promotion/demotion or binding change after M6.5 requires a new explicit Change and Decision,
and may not be justified solely by A-share backtest performance.
