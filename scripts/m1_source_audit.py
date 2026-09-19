from __future__ import annotations

from datetime import date, timedelta

from htcn.data.audit import compare_daily_sources
from htcn.data.providers import AkShareSinaProvider, BaoStockProvider
from htcn.data.validation import normalize_daily

SYMBOLS = ["SSE.688256", "SZSE.300820", "SSE.688300"]


def main() -> int:
    print("[HT-CN M1 AUDIT] Cross-source audit: Sina vs BaoStock", flush=True)
    sina = AkShareSinaProvider()
    bao = BaoStockProvider()

    # Avoid comparing a possibly incomplete current trading day.
    end = date.today() - timedelta(days=1)
    start = end - timedelta(days=120)

    compared = 0
    failures: list[str] = []

    for instrument_id in SYMBOLS:
        print(f"[HT-CN M1 AUDIT] Fetching {instrument_id}...", flush=True)
        try:
            left = normalize_daily(sina.get_daily(instrument_id, start, end))
        except Exception as exc:
            failures.append(f"{instrument_id}: sina unavailable: {exc}")
            print(f"[HT-CN M1 AUDIT] WARN {failures[-1]}", flush=True)
            continue

        try:
            right = normalize_daily(bao.get_daily(instrument_id, start, end))
        except Exception as exc:
            failures.append(f"{instrument_id}: baostock unavailable: {exc}")
            print(f"[HT-CN M1 AUDIT] WARN {failures[-1]}", flush=True)
            continue

        if left.empty or right.empty:
            failures.append(
                f"{instrument_id}: empty source: sina={len(left)} baostock={len(right)}"
            )
            print(f"[HT-CN M1 AUDIT] WARN {failures[-1]}", flush=True)
            continue

        report = compare_daily_sources(left, right)
        compared += 1
        print(
            f"[HT-CN M1 AUDIT] {instrument_id}: overlap={report.overlap_rows}, "
            f"date-only={report.left_only_rows}/{report.right_only_rows}, "
            f"price_mismatch={report.price_mismatches}, "
            f"volume_mismatch={report.volume_mismatches}, "
            f"max_price_diff={report.max_price_abs_diff:.6f}, "
            f"max_volume_rel={report.max_volume_rel_diff:.6%}",
            flush=True,
        )

        # One date difference is tolerated for upstream calendar publication timing,
        # but historical OHLC mismatches are not tolerated.
        if report.overlap_rows < 20:
            failures.append(f"{instrument_id}: insufficient overlap ({report.overlap_rows})")
        if report.price_mismatches:
            failures.append(f"{instrument_id}: {report.price_mismatches} OHLC mismatched rows")
        if report.volume_mismatches:
            failures.append(f"{instrument_id}: {report.volume_mismatches} volume mismatched rows")
        if report.left_only_rows > 1 or report.right_only_rows > 1:
            failures.append(
                f"{instrument_id}: excessive date mismatch "
                f"({report.left_only_rows}/{report.right_only_rows})"
            )

    if compared < 2:
        print(
            f"[HT-CN M1 AUDIT] FAIL: only {compared} symbols could be cross-checked; "
            "need at least 2 independent comparisons.",
            flush=True,
        )
        for failure in failures:
            print(f"  - {failure}", flush=True)
        return 2

    hard_failures = [item for item in failures if "unavailable" not in item]
    if hard_failures:
        print("[HT-CN M1 AUDIT] FAIL", flush=True)
        for failure in hard_failures:
            print(f"  - {failure}", flush=True)
        return 1

    print(f"[HT-CN M1 AUDIT] PASS: compared {compared} symbols", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
