from __future__ import annotations

from pathlib import Path

from htcn.data.catalog import DataCatalog
from htcn.data.health import audit_local_daily
from htcn.data.universe import SUPPORTED_INITIAL_DAILY_PREFIXES


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "market" / "catalog.duckdb"


def main() -> int:
    print("[HT-CN M1 HEALTH] Starting database health check...", flush=True)

    if not CATALOG_PATH.exists():
        print("[HT-CN M1 HEALTH] Database not found.", flush=True)
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    listed = catalog.list_security_ids(listed_only=True)
    in_scope = [
        instrument_id
        for instrument_id in listed
        if instrument_id.startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    ]
    initialized = [
        item
        for item in catalog.list_daily_datasets()
        if str(item["instrument_id"]).startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    ]

    print(f"[HT-CN M1 HEALTH] Catalog          : {CATALOG_PATH}", flush=True)
    print(f"[HT-CN M1 HEALTH] SSE+SZSE scope   : {len(in_scope)}", flush=True)
    print(f"[HT-CN M1 HEALTH] Initialized data : {len(initialized)}", flush=True)
    print("[HT-CN M1 HEALTH] Reading local parquet files...", flush=True)

    def show_progress(done: int, total: int, instrument_id: str) -> None:
        print(
            f"[HT-CN M1 HEALTH] Progress {done}/{total}: {instrument_id}",
            flush=True,
        )

    report = audit_local_daily(catalog, progress=show_progress, progress_every=10)

    print(f"[HT-CN M1 HEALTH] Checked datasets : {report.checked}", flush=True)
    print(f"[HT-CN M1 HEALTH] Not initialized   : {report.uninitialized}", flush=True)
    print(f"[HT-CN M1 HEALTH] Errors            : {len(report.errors)}", flush=True)
    print(f"[HT-CN M1 HEALTH] Warnings          : {len(report.warnings)}", flush=True)

    for issue in report.issues[:50]:
        print(f"[{issue.severity}] {issue.instrument_id}: {issue.message}", flush=True)

    if report.passed:
        print("[HT-CN M1 HEALTH] PASS", flush=True)
        return 0

    print("[HT-CN M1 HEALTH] FAIL", flush=True)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
