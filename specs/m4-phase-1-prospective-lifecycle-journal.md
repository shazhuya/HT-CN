# M4 Phase 1 — Prospective Real-A-Share Lifecycle Journal

## Purpose

Create a clean prospective evidence stream for the M3 canonical Source lifecycle.

M4 Phase 1 does **not** estimate alpha, win rate or trading profitability.

## Prospective boundary

The formal journal starts from the current latest closed A-share session.

Default behavior:

- append-only;
- no historical backfill;
- clean Git worktree;
- exact code HEAD stamped into every entry;
- all captured instruments must align to one closed trade date.

Historical replay, if added later, must use a separately versioned prefix/no-lookahead research protocol and may not be mixed into the prospective ledger.

## Stable candidate identity

Rolling-window bar indexes are not stable across daily captures.

The journal therefore keys a candidate by immutable anchor trade dates:

- XABCD: X / A / B / C;
- standalone AB=CD: A / B / C;
- Shark: 0 / X / A / B.

The terminal point is deliberately excluded so a forming candidate can keep the same identity when it later completes.

5-0 is excluded while production quarantine remains active.

## Journal payload

Each entry records:

- code HEAD;
- instrument and as-of trade date;
- stable candidate key;
- pattern/schema/direction/scale;
- forming/completed geometry state;
- canonical Source lifecycle state;
- Decision Narrative action state;
- next key price / role;
- execution-context gate;
- context-integrity summary;
- Source Raw PRZ bounds;
- Source Terminal trade date when observable;
- explicit `alpha_inference_allowed=false`.

## Atomic daily capture

`scripts/m4_capture_lifecycle_snapshot.py`:

1. requires a clean worktree;
2. reads all initialized listed SSE/SZSE instruments;
3. requires every analysis to end on the same local closed trade date;
4. converts every non-5-0 candidate to journal entries;
5. if any instrument fails, the daily journal is not appended;
6. otherwise appends idempotently to `data/research/m4/lifecycle_journal.jsonl`.

One-click entrypoint:

`运行M4真实A股生命周期快照.bat`.

## Interpretation

Early M4 output is observability and state-transition evidence only.

Do not infer:

- pattern win rates;
- expected return;
- alpha;
- buy/sell ranking;

until a separately frozen statistical protocol exists and enough prospective observations accumulate.


## Cohort enrollment

T0 is a baseline inventory.

- candidates present at T0 are `baseline_existing`;
- candidates first seen after T0 are `prospective_new`;
- only `prospective_new` rows are `prospective_outcome_eligible=true`;
- baseline rows may be used for structural continuity and observability, but not future outcome-rate estimation;
- legacy T0 rows without enrollment fields are normalized as baseline automatically.

## Transition semantics

The derived transition layer is factual, not ranked.

Allowed transition kinds:

- `baseline_observed`;
- `new_candidate`;
- `persisted_same_state`;
- `lifecycle_changed`;
- `action_changed_only`;
- `scanner_disappeared`;
- `scanner_reappeared`.

Important boundaries:

- scanner disappearance is **not** invalidation;
- no linear lifecycle ranking is used because Type-I failure / reaction-only / Type-II branches are not one ordinal ladder;
- reappearing candidates keep their original cohort and first-observed date;
- the append-only journal remains source-of-truth; transition reports are derived and disposable.


## Strict outcome enrollment

`prospective_new` and `prospective_outcome_eligible` are deliberately different.

A candidate may enter the future outcome cohort only when it is:

- first observed after T0;
- still `forming`;
- in a pre-terminal Source lifecycle state;
- backed by a resolved Source Raw PRZ;
- not yet Source-terminal;
- not 5-0;
- not Alternate Bat while its source conflict remains fail-closed.

A candidate first seen unresolved may enroll later if it becomes source-resolved before terminal. The first eligible date becomes `outcome_enrollment_trade_date` and remains frozen.

## T0 quality gate

T0 audit validates:

- one code head / one as-of date;
- unique candidate keys;
- snapshot/journal count agreement;
- full instrument capture;
- lifecycle/action mapping;
- next-key role mapping;
- Source PRZ field consistency;
- Source Terminal date consistency;
- source-fidelity boundaries;
- explicit pattern concentration and observability warnings.

The T0 gate may return transition-ready while outcome-not-ready. This is intentional.
