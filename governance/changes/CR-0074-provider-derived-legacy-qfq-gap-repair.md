# CR-0074 — M7.3 Provider-Derived Legacy QFQ Gap Execution Repair

status: closed
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 882f94581819966cf6d0816454b8e6c5897523ee
target: main
milestone: M7.3

## Trigger

The second real M7 private run on canonical main `882f94581819966cf6d0816454b8e6c5897523ee` still stopped at QFQ 54/55. The uploaded transport bundle SHA-256 is `acf151df60343994720ec2512ecc16528b2fd0f3e284a74d89e9a01d43452309` (22,048 bytes).

`SZSE.000001` again exposed exactly these missing BaoStock factor dates:

- 1991-04-13
- 1991-04-20
- 1991-05-04
- 1991-07-20
- 1991-11-23

All five are Saturdays. AkShare returned an adjusted history but strict normalization rejected non-positive early adjusted OHLC.

## Root cause

D-077 was implemented after a guard that required raw `pre_close` to exist whenever bracket factor drift exceeded the generic 0.5% threshold. For raw histories without `pre_close`, the function executed `continue` before the outside-420-bar legacy bridge was evaluated. Therefore the intended D-077 escape was unreachable on the real provider-derived path.

## Fix

Evaluate the D-077 outside-formal-window legacy bridge before optional `pre_close` continuity. Only if the gap is not eligible for D-077 may historical Saturday repair fall back to the stricter `pre_close` continuity rule.

## Boundaries

No change to the frozen 37-component M4 capture methodology, the frozen 4-component Outcome Engine, harmonic geometry, Source semantics, lifecycle semantics, full-universe QFQ requirement, or statistical-inference boundary.

Inside the frozen 420-bar formal window, a no-`pre_close` gap remains fail-closed.

## Acceptance

See `specs/m7-phase-3-provider-derived-legacy-qfq-gap-repair.md`.

## Closeout

Merged through PR #62 as `7d5fe642c3076a25076ef00c1d96ac7a07e8d079`. Canonical main workflow `35560601018` / `#2435` passed deterministic and formal release-integrity gates, including the immutable 37/4 freeze guards. ISSUE-0069 remains open until the repaired real Private-M1 M7 rerun is independently accepted.
