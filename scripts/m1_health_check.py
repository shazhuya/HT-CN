from __future__ import annotations

from pathlib import Path

from htcn.data.catalog import DataCatalog
from htcn.data.health import audit_local_daily


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "data" / "market" / "catalog.duckdb"


def main() -> int:
    if not CATALOG_PATH.exists():
        print("[HT-CN M1 HEALTH] Database not found.")
        return 1

    catalog = DataCatalog(CATALOG_PATH)
    report = audit_local_daily(catalog)

    print(f"[HT-CN M1 HEALTH] Checked datasets : {report.checked}")
    print(f"[HT-CN M1 HEALTH] Not initialized   : {report.uninitialized}")
    print(f"[HT-CN M1 HEALTH] Errors            : {len(report.errors)}")
    print(f"[HT-CN M1 HEALTH] Warnings          : {len(report.warnings)}")

    for issue in report.issues[:50]:
        print(f"[{issue.severity}] {issue.instrument_id}: {issue.message}")

    if report.passed:
        print("[HT-CN M1 HEALTH] PASS")
        return 0

    print("[HT-CN M1 HEALTH] FAIL")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
