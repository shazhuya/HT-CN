# M7.4 — Post-Five-Day Weekend QFQ Calendar Anomaly Repair

status: closed

## 1. Real evidence

Third real M7 bundle:

- canonical head: `c1be51ef099c11bb5addbb9e501fc195fad433e4`;
- bundle SHA-256: `c56c618c5fedf1e2389240e92998ba32b88e7da932d05c96eb3bd9510769e733`;
- manifest integrity: exact;
- worktree_clean: true;
- methodology: frozen_match_37;
- outcome engine: frozen_match_4;
- M1: latest closed A-share day 2026-09-18, already current;
- QFQ: 54/55;
- failed instrument: `SZSE.000001`;
- BaoStock gaps: 1992-02-01, 1992-02-02, 1993-01-03;
- authoritative committed capture count: 0.

## 2. Historical boundary

Official SZSE chronology records that the exchange began a five-day trading week on 1992-01-01. Therefore Saturday/Sunday raw dates on or after that boundary are treated as legacy raw-calendar anomalies for QFQ factor coverage, not as proof of formal trading sessions.

## 3. Required behavior

For a factor gap whose bracket drift exceeds the generic stable-factor threshold:

1. preserve D-077 for pre-1992 Saturday sessions;
2. identify an all-weekend run on/after 1992-01-01;
3. compute the frozen 420-bar formal-window boundary;
4. only when the entire run is before that boundary, synthesize bounded compatibility factors and audit `fill_rule=legacy_nontrading_weekend_outside_formal_capture_window`;
5. never delete or rewrite raw OHLCV;
6. inside the formal window, fail closed.

## 4. Exact regression

A provider-to-factor regression must omit exactly:

- 1992-02-01;
- 1992-02-02;
- 1993-01-03;

with no raw `pre_close`, force a bracket factor-regime jump, and still produce a strict factor candidate through D-078.

A second regression must prove a post-five-day weekend anomaly inside the formal 420-bar window remains rejected.

## 5. Frozen boundaries

No changes to frozen M4 methodology, Outcome Engine, harmonic Source rules, lifecycle semantics, or statistical inference. ISSUE-0066 remains open.

## 6. Release gate

Require Project OS, Source Coverage, Ruff 0/0, full Python zero-warning suite, Web, browser acceptance, Phase18, Phase21, methodology 37/37 and Outcome 4/4. Only after canonical-main success may the Private-M1 M7 BAT be rerun.
