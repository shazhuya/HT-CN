# M6.5 — Source Coverage Freeze

status: closed

## 1. Objective

Freeze the HT-CN capability surface derived from Scott M. Carney Harmonic Trading Volumes One,
Two and Three so that product, research and future chart work cannot silently reinterpret what is
supported.

## 2. Taxonomy

Every Source capability is exactly one of Supported / Partial / Quarantined / Unsupported.
There are no current Partial items. Unresolved Source conflict is represented as Quarantined or
Unsupported, not softened into Partial.

## 3. Required bindings

Each supported/quarantined capability binds:

- Source ledger/reference;
- active/frozen spec;
- runtime/research code path;
- deterministic test path;
- governing Decision.

Unsupported capabilities bind Source/spec/Decision evidence and must not claim implementation code
or tests.

## 4. Critical frozen states

The machine verifier must fail closed if any of these drift:

- FIVE_ZERO != quarantined;
- ALTERNATE_BAT != quarantined or production_state != fail_closed;
- SHARK topology != 0XABC or loses the never-fabricate-D constraint;
- HSI != unsupported;
- RSI_BAMM_ACCELERATION_TRIGGER != unsupported/deferred;
- current Partial item set becomes non-empty without an explicit new Decision;
- a bound Source/spec/code/test/Decision path is missing;
- source-fidelity status contradicts the coverage ledger on 5-0, Alternate Bat or BAMM acceleration.

## 5. CI requirement

`scripts/m6_verify_source_coverage.py` runs in the main CI immediately after Project OS validation.
Any Source coverage drift fails CI.

## 6. Non-goals

M6.5 does not change harmonic formulas, Raw PRZ membership, lifecycle clocks, 5-0/Alternate Bat
production status, empirical thresholds, M4 evidence, A-share execution rules, or trading behavior.

## 7. Exit gate

M6.5 may close only after:

1. schema-2 coverage ledger validates;
2. all critical states/bindings are machine-checked;
3. CI concurrency hardening is validated;
4. Project OS, Ruff 0, Python, Web, browser, Phase18, Phase21, M4 37/37 and Outcome 4/4 are green;
5. PR and post-merge canonical-main validation are green;
6. Project State / Milestones / Attempt / Decision ledgers agree;
7. M6.6 becomes the next major task.


## 8. Closeout evidence

M6.5 was merged through PR #56 as canonical main commit
`beb6688fb3faf9dcdd71fb8f8c754aaff32e8daf`. Main workflow `35485499183` / #2369 passed
Project OS, Source Coverage verification, Ruff 0/0, 896 Python tests with 0 warnings, Web/browser,
Phase18, Phase21, M4 methodology 37/37 and Outcome Engine 4/4.

The frozen ledger contains 18 capabilities with zero current Partial items. FIVE_ZERO remains
quarantined, ALTERNATE_BAT remains fail-closed/quarantined, HSI remains unsupported and the RSI
BAMM Acceleration Trigger remains deferred/unsupported.
