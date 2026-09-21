# M7.3 — Provider-Derived Legacy QFQ Gap Execution Repair

status: planned

## 1. Real failure evidence

Canonical head: `882f94581819966cf6d0816454b8e6c5897523ee`.

Second real M7 run:

- M1: pass;
- strict QFQ: 54/55;
- failed instrument: `SZSE.000001`;
- BaoStock missing dates: 1991-04-13, 1991-04-20, 1991-05-04, 1991-07-20, 1991-11-23;
- authoritative capture: not committed;
- failure transport bundle: clean/current-run only, confirming M7.2 stale-report cleanup.

## 2. Required execution order

For a bracketed factor gap whose drift exceeds the generic stable-factor threshold:

1. identify whether every missing raw session is a Saturday from 1992 or earlier;
2. compute the frozen 420-bar formal-window start;
3. if the entire gap is strictly before that window, apply D-077 immediately and audit `fill_rule=legacy_saturday_outside_formal_capture_window`;
4. only when D-077 does not apply may the older historical-Saturday path require raw `pre_close` continuity;
5. if the gap is inside the formal window and `pre_close` is unavailable, fail closed.

## 3. Exact regression

A provider-to-factor regression must omit exactly the five real 1991 Saturday dates above, omit raw `pre_close`, and still prove a strict factor candidate after five audited D-077 repairs.

A second regression must prove a no-`pre_close` Saturday gap inside the formal window remains rejected.

## 4. Frozen boundaries

No frozen M4 methodology or Outcome Engine path may change. No committed evidence may be rewritten. No early win-rate, alpha or profitability inference is authorized.

## 5. Release gates

Before merge: Project OS, Source Coverage, Ruff 0/0, full Python zero-warning suite, Web, browser acceptance, Phase18, Phase21, methodology 37/37 and Outcome Engine 4/4 must all pass.

After canonical-main validation, rerun only `运行M7前瞻证据积累.bat`. ISSUE-0069 closes only after the resulting real evidence bundle is independently accepted.
