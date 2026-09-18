from __future__ import annotations

import argparse
import json
from datetime import date, datetime, time as clock_time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

from htcn.data.benchmarks import CORE_BENCHMARKS, CoreBenchmarkStore
from htcn.data.providers import AkShareProvider


SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")
POST_CLOSE_CUTOFF = clock_time(16, 30)


def _default_end() -> date:
    now = datetime.now(SHANGHAI_TZ)
    return (
        now.date()
        if now.timetz().replace(tzinfo=None) >= POST_CLOSE_CUTOFF
        else now.date() - timedelta(days=1)
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="HT-CN M3 core benchmark sync")
    parser.add_argument("--root", default="data/market/benchmarks")
    parser.add_argument("--start", default="2024-01-01")
    parser.add_argument("--end", default=None)
    parser.add_argument(
        "--output",
        default="artifacts/reports/m3-core-benchmark-sync.json",
    )
    args = parser.parse_args()

    start = date.fromisoformat(args.start)
    end = date.fromisoformat(args.end) if args.end else _default_end()
    store = CoreBenchmarkStore(args.root)
    provider = AkShareProvider()
    results = []

    for spec in CORE_BENCHMARKS:
        try:
            existing = store.read(spec.key)
            fetch_start = start
            if not existing.empty:
                latest = pd.Timestamp(existing["trade_date"].max()).date()
                fetch_start = max(start, latest + timedelta(days=1))
            if fetch_start <= end:
                incoming = provider.get_index_daily(spec.symbol, fetch_start, end)
                merged = store.upsert(spec.key, incoming) if not incoming.empty else existing
            else:
                merged = existing
            results.append(
                {
                    "key": spec.key,
                    "symbol": spec.symbol,
                    "name_zh": spec.name_zh,
                    "status": "ok" if not merged.empty else "empty",
                    "rows": len(merged),
                    "last_trade_date": (
                        None
                        if merged.empty
                        else pd.Timestamp(merged["trade_date"].max()).date().isoformat()
                    ),
                }
            )
        except Exception as exc:
            results.append(
                {
                    "key": spec.key,
                    "symbol": spec.symbol,
                    "name_zh": spec.name_zh,
                    "status": "failed",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )

    payload = {
        "schema_version": 1,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "results": results,
    }
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M3] report: {output}")
    return 0 if all(item["status"] == "ok" for item in results) else 2


if __name__ == "__main__":
    raise SystemExit(main())
