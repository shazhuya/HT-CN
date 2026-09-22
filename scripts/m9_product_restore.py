from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.product_backup import restore_product_backup, verify_product_backup

ROOT = Path(__file__).resolve().parents[1]


def _latest_backup() -> Path:
    rows = sorted(
        (ROOT / "backups").glob("htcn-*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not rows:
        raise FileNotFoundError("没有可恢复的 HT-CN 备份。")
    return rows[0]


def main() -> int:
    parser = argparse.ArgumentParser(description="Restore verified HT-CN product backup")
    parser.add_argument("archive", nargs="?", default=None)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    archive = Path(args.archive) if args.archive else _latest_backup()
    if args.verify_only:
        payload = verify_product_backup(archive)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("verified") else 2
    payload = restore_product_backup(root=ROOT, archive_path=archive)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
