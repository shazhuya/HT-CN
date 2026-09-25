from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pandas as pd

from htcn.data.intraday import AkShareIntradayProvider, IntradayProviderError
from htcn.data.providers.akshare_provider import AkShareProvider
from htcn.data.providers.baostock_provider import BaoStockProvider
from htcn.harmonic.pine_r34 import PINE_R34_SOURCE_SHA256, scan_pine_r34

CORPUS: tuple[tuple[str, str, str], ...] = (
    ("SSE.688256", "寒武纪", "STAR_AI"),
    ("SZSE.300394", "天孚通信", "CPO"),
    ("SZSE.300750", "宁德时代", "growth_battery"),
    ("SSE.688012", "中微公司", "STAR_semiconductor"),
    ("SZSE.002594", "比亚迪", "auto"),
    ("SSE.600519", "贵州茅台", "consumption"),
    ("SSE.600036", "招商银行", "bank"),
    ("SSE.601318", "中国平安", "insurance"),
    ("SSE.601899", "紫金矿业", "resources"),
    ("SZSE.000333", "美的集团", "industrial_consumer"),
)

TIMEFRAMES = ("1d", "60m", "15m")
MIN_ROWS = {"1d": 240, "60m": 240, "15m": 480}
MAX_SCAN_BARS = {"1d": 720, "60m": 720, "15m": 1200}
REPORT_PATH = Path("artifacts/reports/m9-recognition-real-market-acceptance.json")


def _frame_digest(frame: pd.DataFrame, *, time_column: str) -> str:
    columns = [time_column, "open", "high", "low", "close", "volume"]
    available = [column for column in columns if column in frame.columns]
    canonical = frame[available].copy()
    canonical[time_column] = pd.to_datetime(canonical[time_column]).astype(str)
    payload = canonical.to_csv(index=False, float_format="%.10g").encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate_sample(scan, limit: int = 8) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for item in scan.live_candidates[:limit]:
        rows.append(
            {
                "pattern_id": item.pattern_id,
                "direction": "bullish" if item.direction == 1 else "bearish",
                "scale": item.scale,
                "research_only": item.research_only,
                "qualified": item.qualified,
                "precise": item.precise,
                "source_nodes": [
                    {
                        "label": label,
                        "index": node.index,
                        "price": node.price,
                        "confirmed_at": node.confirmed_at,
                    }
                    for label, node in zip(
                        item.source_labels,
                        item.source_nodes,
                        strict=True,
                    )
                ],
                "prz_low": item.prz_low,
                "prz_high": item.prz_high,
                "structural_limit": item.structural_limit,
                "born_bar": item.born_bar,
                "first_test_bar": item.first_test_bar,
            }
        )
    return rows


def _scan_record(
    *,
    instrument_id: str,
    name: str,
    segment: str,
    timeframe: str,
    provider: str,
    adjustment: str,
    frame: pd.DataFrame,
    time_column: str,
) -> dict[str, Any]:
    selected = frame.tail(MAX_SCAN_BARS[timeframe]).reset_index(drop=True)
    scan = scan_pine_r34(selected)
    born_counts = {
        str(key): int(value)
        for key, value in dict(scan.diagnostics.get("born_counts") or {}).items()
    }
    candidates = list(scan.candidates)
    standard_stored = sum(not item.research_only for item in candidates)
    research_stored = sum(item.research_only for item in candidates)
    return {
        "instrument_id": instrument_id,
        "name": name,
        "segment": segment,
        "timeframe": timeframe,
        "status": "ok",
        "provider": provider,
        "adjustment": adjustment,
        "rows_available": len(frame),
        "rows_scanned": len(selected),
        "first_bar": str(pd.Timestamp(selected[time_column].iloc[0])),
        "last_bar": str(pd.Timestamp(selected[time_column].iloc[-1])),
        "ohlcv_sha256": _frame_digest(selected, time_column=time_column),
        "historical_birth_count": sum(born_counts.values()),
        "born_counts": born_counts,
        "stored_candidate_count": len(candidates),
        "stored_standard_candidate_count": standard_stored,
        "stored_research_candidate_count": research_stored,
        "live_candidate_count": len(scan.live_candidates),
        "live_standard_candidate_count": sum(
            not item.research_only for item in scan.live_candidates
        ),
        "candidate_sample": _candidate_sample(scan),
    }


def _fetch_daily(
    primary: AkShareProvider,
    fallback: BaoStockProvider,
    instrument_id: str,
    *,
    start: date,
    end: date,
    attempts: int = 2,
) -> tuple[pd.DataFrame, str]:
    failures: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            frame = primary.get_daily_adjusted(
                instrument_id,
                start,
                end,
                mode="qfq",
            ).sort_values("trade_date").reset_index(drop=True)
            if not frame.empty:
                return frame, "akshare_eastmoney"
            failures.append(f"akshare attempt={attempt}: empty")
        except (ConnectionError, RuntimeError, ValueError, TypeError, OSError) as exc:
            failures.append(f"akshare attempt={attempt}:{type(exc).__name__}:{exc}")
        if attempt < attempts:
            time.sleep(attempt)

    try:
        frame = fallback.get_daily_adjusted(
            instrument_id,
            start,
            end,
            mode="qfq",
        ).sort_values("trade_date").reset_index(drop=True)
        if not frame.empty:
            return frame, "baostock"
        failures.append("baostock: empty")
    except (ConnectionError, RuntimeError, ValueError, TypeError, OSError) as exc:
        failures.append(f"baostock:{type(exc).__name__}:{exc}")

    raise RuntimeError(
        f"no daily QFQ provider succeeded for {instrument_id}: "
        + " | ".join(failures)
    )


def _retry_intraday(
    provider: AkShareIntradayProvider,
    instrument_id: str,
    *,
    timeframe: str,
    start: datetime,
    end: datetime,
    attempts: int = 3,
):
    failures: list[str] = []
    for attempt in range(1, attempts + 1):
        try:
            return provider.fetch(
                instrument_id,
                timeframe=timeframe,
                start=start,
                end=end,
                adjust="qfq",
            )
        except (IntradayProviderError, RuntimeError, ValueError, TypeError, OSError) as exc:
            failures.append(f"attempt={attempt}:{type(exc).__name__}:{exc}")
            if attempt < attempts:
                time.sleep(2 * attempt)
    raise IntradayProviderError(" | ".join(failures))


def _failure_record(
    *,
    instrument_id: str,
    name: str,
    segment: str,
    timeframe: str,
    exc: BaseException,
) -> dict[str, Any]:
    return {
        "instrument_id": instrument_id,
        "name": name,
        "segment": segment,
        "timeframe": timeframe,
        "status": "failed",
        "error_type": type(exc).__name__,
        "error": str(exc)[:1000],
    }


def build_report() -> dict[str, Any]:
    shanghai = ZoneInfo("Asia/Shanghai")
    now = datetime.now(tz=shanghai)
    daily_start = (now - timedelta(days=1100)).date()
    intraday_start = (now - timedelta(days=190)).replace(tzinfo=None)
    intraday_end = now.replace(tzinfo=None)

    daily_provider = AkShareProvider()
    daily_fallback = BaoStockProvider()
    intraday_provider = AkShareIntradayProvider()
    series: list[dict[str, Any]] = []

    for instrument_id, name, segment in CORPUS:
        try:
            daily, daily_source = _fetch_daily(
                daily_provider,
                daily_fallback,
                instrument_id,
                start=daily_start,
                end=now.date(),
            )
            if len(daily) < MIN_ROWS["1d"]:
                raise RuntimeError(
                    f"daily rows {len(daily)} < required {MIN_ROWS['1d']}"
                )
            series.append(
                _scan_record(
                    instrument_id=instrument_id,
                    name=name,
                    segment=segment,
                    timeframe="1d",
                    provider=daily_source,
                    adjustment="qfq",
                    frame=daily,
                    time_column="trade_date",
                )
            )
        except Exception as exc:  # noqa: BLE001 - acceptance must record provider failures
            series.append(
                _failure_record(
                    instrument_id=instrument_id,
                    name=name,
                    segment=segment,
                    timeframe="1d",
                    exc=exc,
                )
            )

        for timeframe in ("60m", "15m"):
            try:
                market = _retry_intraday(
                    intraday_provider,
                    instrument_id,
                    timeframe=timeframe,
                    start=intraday_start,
                    end=intraday_end,
                )
                if len(market.frame) < MIN_ROWS[timeframe]:
                    raise RuntimeError(
                        f"{timeframe} rows {len(market.frame)} < required "
                        f"{MIN_ROWS[timeframe]}"
                    )
                series.append(
                    _scan_record(
                        instrument_id=instrument_id,
                        name=name,
                        segment=segment,
                        timeframe=timeframe,
                        provider=market.provider,
                        adjustment=market.adjustment,
                        frame=market.frame,
                        time_column="trade_time",
                    )
                )
            except Exception as exc:  # noqa: BLE001 - acceptance must record provider failures
                series.append(
                    _failure_record(
                        instrument_id=instrument_id,
                        name=name,
                        segment=segment,
                        timeframe=timeframe,
                        exc=exc,
                    )
                )

    successful = [row for row in series if row["status"] == "ok"]
    failed = [row for row in series if row["status"] != "ok"]
    by_timeframe: dict[str, dict[str, Any]] = {}
    for timeframe in TIMEFRAMES:
        scoped = [row for row in series if row["timeframe"] == timeframe]
        ok = [row for row in scoped if row["status"] == "ok"]
        births = sum(int(row["historical_birth_count"]) for row in ok)
        live = sum(int(row["live_candidate_count"]) for row in ok)
        standard = sum(int(row["stored_standard_candidate_count"]) for row in ok)
        families: Counter[str] = Counter()
        for row in ok:
            families.update(row["born_counts"])
        by_timeframe[timeframe] = {
            "requested_series": len(scoped),
            "successful_series": len(ok),
            "coverage_ratio": len(ok) / max(len(scoped), 1),
            "historical_birth_count": births,
            "stored_standard_candidate_count": standard,
            "live_candidate_count": live,
            "families": dict(sorted(families.items())),
        }

    total_births = sum(
        int(row["historical_birth_count"]) for row in successful
    )
    total_standard = sum(
        int(row["stored_standard_candidate_count"]) for row in successful
    )
    total_live = sum(int(row["live_candidate_count"]) for row in successful)
    family_set = {
        family
        for row in successful
        for family, count in row["born_counts"].items()
        if int(count) > 0
    }

    gates = {
        "daily_coverage": by_timeframe["1d"]["coverage_ratio"] >= 0.7,
        "60m_coverage": by_timeframe["60m"]["coverage_ratio"] >= 0.7,
        "15m_coverage": by_timeframe["15m"]["coverage_ratio"] >= 0.7,
        "recognition_not_near_zero": total_births >= max(20, len(successful)),
        "standard_family_output_exists": total_standard >= max(5, len(successful) // 3),
        "family_diversity": len(family_set) >= 3,
        "current_live_monitoring_exists": total_live >= 1,
    }
    status = "pass" if all(gates.values()) else "fail"
    return {
        "schema": 1,
        "acceptance_id": "m9-cr0089-real-market-recognition-v1",
        "status": status,
        "generated_at": now.isoformat(),
        "pine_r34_source_sha256": PINE_R34_SOURCE_SHA256,
        "corpus_size": len(CORPUS),
        "requested_series": len(series),
        "successful_series": len(successful),
        "failed_series": len(failed),
        "timeframes": by_timeframe,
        "totals": {
            "historical_birth_count": total_births,
            "stored_standard_candidate_count": total_standard,
            "live_candidate_count": total_live,
            "distinct_families": sorted(family_set),
        },
        "gates": gates,
        "series": series,
        "claims_boundary": (
            "This validates recognition/data operability only. It is not a win-rate, alpha, "
            "profitability or statistical-significance claim."
        ),
        "user_computer_used": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, default=REPORT_PATH)
    parser.add_argument("--no-fail", action="store_true")
    args = parser.parse_args()

    report = build_report()
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "pass" or args.no_fail else 2


if __name__ == "__main__":
    raise SystemExit(main())
