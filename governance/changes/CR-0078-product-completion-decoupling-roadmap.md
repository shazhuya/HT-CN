# CR-0078 — M9.0 Product Completion Decoupling and Automation Roadmap

status: ready_to_merge
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: 87a59ecc0bc26cba65f4fdba116218745947b444
target: main
milestone: M9.0

## Trigger

After M7.6 closeout, PROJECT_STATE still pointed the next major task at continuous M7 evidence accumulation. That is correct as a background research operation but wrong as the product-development mainline. The user explicitly rejected a workflow that would require daily local Private-M1/BAT/ZIP operation for months or years.

## Objective

1. Make the M9 productization program the development mainline.
2. Keep M7 prospective evidence running as a non-blocking background track.
3. Keep M8/ISSUE-0066 as a claims/calibration gate only.
4. Freeze a stable-product completion definition that does not depend on natural-time sample accumulation.
5. Make routine user-computer dependency a policy violation.
6. Persist the policy into Project OS, Resume Pack and portable chat continuation so future AI handoffs cannot silently revert.
7. Define M9.1-M9.6 implementation phases.

## Non-goals

- no change to harmonic Source truth;
- no change to M4 methodology or Outcome Engine;
- no relaxation of ISSUE-0066 statistical restrictions;
- no automatic trading;
- no historical evidence backfill.

## Acceptance

See `specs/m9-phase-0-product-completion-decoupling.md`.
