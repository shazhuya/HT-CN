# CR-0075 — M7.4 Post-Five-Day Weekend QFQ Calendar Anomaly Repair

status: implementing
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: c1be51ef099c11bb5addbb9e501fc195fad433e4
target: main
milestone: M7.4

## Trigger

The third real M7 run on canonical main `c1be51ef099c11bb5addbb9e501fc195fad433e4` produced a valid transport bundle (SHA-256 `c56c618c5fedf1e2389240e92998ba32b88e7da932d05c96eb3bd9510769e733`, 22,110 bytes), kept both immutable freeze guards green, and passed M1, but strict QFQ remained 54/55.

M7.3 successfully removed the five 1991 Saturday gaps. The remaining BaoStock gaps for `SZSE.000001` are:

- 1992-02-01
- 1992-02-02
- 1993-01-03

## Root cause

D-077 correctly modeled genuine early Saturday sessions, but the next provider/raw mismatch crosses a historical market-rule boundary. SZSE's official chronology states that a five-day trading week began on 1992-01-01. Therefore weekend raw rows on/after that date must not be generalized as real weekend trading sessions.

## Fix

Implement D-078:

- preserve raw OHLCV unchanged;
- classify post-1992-01-01 Saturday/Sunday raw rows as legacy calendar anomalies;
- allow a deterministic audited factor bridge only when the entire missing run is strictly before the frozen 420-bar formal window;
- keep any such anomaly inside the formal window fail-closed;
- retain pre-1992 Saturday semantics under D-077.

## Acceptance

See `specs/m7-phase-4-post-five-day-weekend-qfq-anomaly.md`.
