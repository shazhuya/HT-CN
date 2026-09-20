# D-077 — Legacy Saturday QFQ calendar holes may be bridged only outside the frozen formal-capture window

status: `active`

## Decision

M7 strict QFQ preparation may synthesize factors for an early A-share Saturday provider-calendar hole only when the missing run is internal, bracketed by real factors, year 1992 or earlier, and strictly outside the frozen 420-bar formal prospective-capture window. The bridge uses deterministic linear interpolation and is audited as `legacy_saturday_outside_formal_capture_window`.

Existing local factor files are inspected and safely repaired before a network refetch.

## Rationale

The first real M7 append was blocked by five 1991 Saturday raw sessions in `SZSE.000001` absent from BaoStock adjusted history while AkShare was temporarily unavailable. Those sessions cannot enter the frozen 420-bar 2026 formal analysis window. Blocking the entire current formal view on that legacy provider-calendar mismatch is an operational preparation defect, not a harmonic-methodology safeguard.

## Boundaries

The full initialized SSE/SZSE universe remains required; any gap inside the 420-bar window remains fail-closed; raw OHLCV and committed evidence are never rewritten; frozen M4/Outcome components do not change; this decision authorizes no statistical or trading claim.
