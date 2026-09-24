# CR-0088 — Recognition recall and observable CD-leg research

status: planned
baseline_ref: main
baseline_head: 9e228d204082fe19d169e099da16ade11adac658
implementation_baseline_head: b412ffd8eb5e82416b46a8235fc9d6d68702a858
target: main
milestone: M9.post_release
work_branch: m9/recognition-recall-audit

## Trigger

The user reports that the shipped app detects almost nothing and lacks the practical XABC-to-CD-leg scenario projection available in the independent R3.1–R3.5 and Pine 6.7.1 projects. The chart-first UI acceptance did not test recognition recall on independently labeled real bars. This is a product-acceptance defect, not a claim about trade returns. ISSUE-0073 tracks the gate.

## Baseline and findings

See `specs/m9-post-release-recognition-recall.md` for exact source files, data hashes, measured counts, limits and reproduction. Two actual 688256 **daily** OHLC files independently produce zero current standard XABCD forming and zero completed results with production scales. This is not an hourly-screen parity test. A source-shaped synthetic Gartley with exactly 0.786 D/XA is accepted, whereas moving D by 0.01 price unit rejects the completed identity even though the XABC projection remains. This is the current exact identity rule, not proof that a completed near miss should be promoted.

## Objective

Establish reproducible real-data recall and false-positive audit first; then develop a separately typed, time-valid candidate/nearby/conditional CD-leg scenario channel with projected measurements and explicit failure/expiry, distinct from Source-valid forming and completed identities. Show why each candidate does or does not qualify in the chart/inspector. Compare the same instrument, bar interval, price basis, pivot settings and time-of-knowledge against the actual Pine implementations; preserve source rules and no-lookahead.

## Non-goals and boundaries

Do not score-rescue Source identity, broaden D/XA or C/AB frozen constraints by fiat, convert a projected price into an observed D/Terminal, paint future K lines, reclassify quarantined 5-0/Alternate Bat, edit M4 methodology/Outcome, or claim win rate/profitability. R3 is a reference implementation, not an authoritative Source specification; v6.7.1 can average away a missing necessary ratio and includes quarantined identities. Keep product research candidates separate from execution and evidence.

## Acceptance gates

1. A fixed, independently reviewable set of real daily and hourly OHLC cases, with instrument, period, QFQ/raw basis, SHA-256, Pine settings and human-labeled visible candidates plus false-positive counterexamples. Do not substitute daily bars for the user's hourly example.
2. Stage-by-stage counts for valid bars, pivot events, confirmed frontier, XABC B/C band, harmonic-family gate, PRZ projection, completed geometry and displayed state, compared to Pine R3.1–R3.5 and 6.7.1 under equivalent settings. Classify mismatches as data, topology, ratio, projection, time, lifecycle or UI.
3. Preserve original strict Source-valid channel and all frozen gates. Candidate channel may project conditional D but must declare its own evidence grade, uncertainty, stale/invalid status and lack of Source identity/Raw PRZ; do not backfill from future information.
4. Regression on real accepted positive and negative cases, partial-leg/live replay, no-lookahead, price-basis drift, latency and empty-state explanation. Published recall numerator/denominator and false-positive count must be tied to that test set, never called accuracy or trading performance without evidence.
5. Formal hosted CI plus Project OS/Source Coverage, M4 37/37, Outcome 4/4, Python/Web/browser and user-centered chart acceptance before merge and postmerge closeout.

## Current gate and next action

Research audit complete on baseline; implementation is **not** started and the recognition defect is **not** fixed. Next: freeze a labeled replay corpus from the already accessible daily bars, obtain the same-timeframe 688256 hourly OHLC (public provider or one bounded export if access cannot be automated), and implement a non-authoritative candidate lane with temporal invalidation as a separately reviewed patch. The daily corpus can start implementation; the hourly UAT parity gate cannot be claimed from a screenshot or daily substitution.
