from __future__ import annotations

from pathlib import Path

from htcn.data.catalog import DataCatalog
from htcn.data.universe import SUPPORTED_INITIAL_DAILY_PREFIXES

ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "market" / "catalog.duckdb"


def main() -> int:
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 STATUS] Database not found. Run pilot/full initializer first.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    securities = catalog.security_count()
    listed_ids = catalog.list_security_ids(listed_only=True)
    supported = [
        instrument_id
        for instrument_id in listed_ids
        if instrument_id.startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    ]
    supported_set = set(supported)
    deferred_bse = sum(instrument_id.startswith("BSE.") for instrument_id in listed_ids)

    dataset_rows = catalog.list_daily_datasets()
    in_scope_datasets = sum(
        str(row["instrument_id"]) in supported_set for row in dataset_rows
    )
    out_of_scope_datasets = len(dataset_rows) - in_scope_datasets
    counts = catalog.task_counts()
    pct = (in_scope_datasets / len(supported) * 100.0) if supported else 0.0

    print(f"[HT-CN M1 STATUS] Securities total      : {securities}")
    print(f"[HT-CN M1 STATUS] SSE+SZSE in scope     : {len(supported)}")
    print(f"[HT-CN M1 STATUS] BSE out of scope      : {deferred_bse}")
    print(
        f"[HT-CN M1 STATUS] Daily data in scope   : {in_scope_datasets} "
        f"({pct:.2f}% of in-scope)"
    )
    print(f"[HT-CN M1 STATUS] Daily data out of scope: {out_of_scope_datasets}")
    print(f"[HT-CN M1 STATUS] Calendar              : {catalog.calendar_count()} trading days")
    print(f"[HT-CN M1 STATUS] Tasks                 : {counts}")

    failed = [item for item in catalog.failed_tasks(limit=50) if not item["instrument_id"].startswith("BSE.")]
    if failed:
        print("[HT-CN M1 STATUS] Recent in-scope failures:")
        for item in failed[:10]:
            print(
                f"  {item['instrument_id']} attempts={item['attempt_count']} "
                f"error={item['error_message']}"
            )
    else:
        print("[HT-CN M1 STATUS] Recent in-scope failures: none")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
