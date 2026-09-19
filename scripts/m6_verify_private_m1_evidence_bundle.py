from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.private_m1_closeout import verify_private_m1_evidence_bundle

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = (
    ROOT
    / "artifacts"
    / "reports"
    / "htcn-m6-private-m1-closeout-evidence.zip"
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify one portable M6.2 private-M1 closeout evidence ZIP"
    )
    parser.add_argument("bundle", nargs="?", type=Path, default=DEFAULT)
    args = parser.parse_args()
    path = args.bundle
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    payload = verify_private_m1_evidence_bundle(path)
    print(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
    )
    return 0 if payload["status"] == "valid" else 2


if __name__ == "__main__":
    raise SystemExit(main())
