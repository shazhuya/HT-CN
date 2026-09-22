# M9.6 — Stable Product Release Acceptance

status: planned

## 1. Stable release meaning

HT-CN Stable v1.0.0 means the product runtime is complete and formally releasable:
- automated market data;
- automated harmonic analysis;
- integrated workbench;
- background prospective evidence;
- supervised/recoverable zero-CLI operation;
- versioned verified release package.

It does not mean empirical win-rate, alpha, profitability or statistical significance is established.

## 2. Version identity

- project/package/API/stable contract version is 1.0.0;
- formal release ZIP manifest must report release_version=1.0.0;
- UI/API acceptance must expose the same stable version;
- version mismatch fails closed.

## 3. Stable Product Contract

Machine-readable governance must state:
- M9 product capabilities available;
- automatic trading unavailable;
- ISSUE-0066 statistical claim surfaces unavailable;
- M7 continues in the background after release;
- M8 activates only under its existing evidence authorization boundary;
- FIVE_ZERO quarantined, Alternate Bat fail-closed, HSI unsupported.

## 4. End-to-end acceptance

The stable acceptance report must verify:
- M9.0-M9.5 are closed;
- M9.6 is the active/ready/closed stable-release phase;
- Product Completion Policy allows release with ISSUE-0066 open;
- ISSUE-0066 remains claims-only;
- all prohibited statistical claim flags are false;
- release package verification succeeded;
- extracted package had git_present=false;
- extracted package M4 methodology guard, Outcome Engine guard and product supervisor preflight all exit 0;
- release package excludes mutable/private market data;
- zero-CLI start/stop/backup/restore/update entrypoints exist;
- operator runbook and recovery contract exist;
- no automatic trading is enabled.

## 5. Operator documentation

The release must include:
- operator runbook: install/start/stop, daily use, evidence-insufficient behavior, update, backup, health and troubleshooting;
- recovery contract: identity verification, crash-loop, backup verification, restore staging, update rollback, schema migration and user-computer exception boundaries;
- v1.0.0 release notes with supported/unsupported capabilities.

## 6. Formal CI

Formal main-release CI must:
1. build Web;
2. build and verify v1.0.0 release ZIP;
3. run stable-release acceptance against that exact ZIP/report;
4. run all browser tests including stable-release acceptance;
5. run Phase18 and Phase21;
6. verify M4 37/37 and Outcome 4/4;
7. upload stable acceptance report and release ZIP as formal release artifacts.

## 7. M9 closeout

After exact ledger-bearing PR validation and canonical-main validation:
- write final governance/releases/<main-commit>.json stable release record;
- mark M9.6 closed;
- mark M9 Stable Research/Product Release closed;
- next product state becomes stable_released;
- M7 background evidence continues and M8 remains unavailable until evidence authorization permits it.

## 8. Exit gate

M9.6 closes only when every milestone exit gate and the exact canonical-main stable acceptance are green.
