from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.app.release_identity import verify_release_identity
from htcn.app.release_package import verify_release_package


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify HT-CN installed or ZIP release identity")
    parser.add_argument("target", nargs="?", default=".")
    args = parser.parse_args()
    target = Path(args.target)
    if target.is_file():
        payload = verify_release_package(target)
        ok = bool(payload.get("verified"))
    else:
        result = verify_release_identity(target)
        payload = result.as_payload()
        ok = result.verified
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
