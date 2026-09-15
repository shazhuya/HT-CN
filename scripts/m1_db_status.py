from __future__ import annotations

from pathlib import Path

from htcn.data.catalog import DataCatalog


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "market" / "catalog.duckdb"


def main() -> int:
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 STATUS] Database not found. Run pilot/full initializer first.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    securities = catalog.security_count()
    datasets = catalog.daily_dataset_count()
    counts = catalog.task_counts()
    pct = (datasets / securities * 100.0) if securities else 0.0

    print(f"[HT-CN M1 STATUS] Securities : {securities}")
    print(f"[HT-CN M1 STATUS] Daily data  : {datasets} ({pct:.2f}%)")
    print(f"[HT-CN M1 STATUS] Calendar    : {catalog.calendar_count()} trading days")
    print(f"[HT-CN M1 STATUS] Tasks       : {counts}")

    failed = catalog.failed_tasks(limit=10)
    if failed:
        print("[HT-CN M1 STATUS] Recent failures:")
        for item in failed:
            print(
                f"  {item['instrument_id']} attempts={item['attempt_count']} "
                f"error={item['error_message']}"
            )
    else:
        print("[HT-CN M1 STATUS] Recent failures: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
