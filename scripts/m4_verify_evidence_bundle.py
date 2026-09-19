from __future__ import annotations

import argparse
import json
from pathlib import Path

from htcn.research.evidence_bundle import verify_evidence_bundle


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Verify the structural integrity of an M4 evidence transport bundle."
    )
    parser.add_argument(
        "bundle",
        nargs="?",
        default="artifacts/reports/m4-evidence-bundle.zip",
    )
    args = parser.parse_args()

    result = verify_evidence_bundle(Path(args.bundle))
    print(json.dumps(result.as_payload(), ensure_ascii=False, indent=2))
    return 0 if result.status == "valid" else 1


if __name__ == "__main__":
    raise SystemExit(main())
