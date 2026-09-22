from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.product_backup import create_product_backup, prune_backups

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    parser = argparse.ArgumentParser(description="Create verified HT-CN product backup")
    parser.add_argument("--keep", type=int, default=7)
    parser.add_argument("--label", default="manual")
    args = parser.parse_args()
    payload = create_product_backup(root=ROOT, label=str(args.label))
    payload["pruned"] = prune_backups(ROOT, keep=max(1, int(args.keep)))
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
