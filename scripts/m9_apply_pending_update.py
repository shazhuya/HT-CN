from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from htcn.app.product_update import apply_verified_update
from htcn.app.release_package import verify_release_package

ROOT = Path(__file__).resolve().parents[1]


def _latest_pending() -> Path:
    rows = sorted(
        (ROOT / "updates").glob("*.zip"),
        key=lambda item: item.stat().st_mtime,
        reverse=True,
    )
    if not rows:
        raise FileNotFoundError("updates 目录没有待安装的 verified release ZIP。")
    return rows[0]


def _refresh_dependencies(root: Path) -> int:
    process = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-e", str(root)],
        cwd=root,
        check=False,
    )
    return int(process.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply verified HT-CN pending update")
    parser.add_argument("package", nargs="?", default=None)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    package = Path(args.package) if args.package else _latest_pending()
    if args.verify_only:
        payload = verify_release_package(package)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0 if payload.get("verified") else 2
    payload = apply_verified_update(
        root=ROOT,
        package_path=package,
        dependency_refresh=_refresh_dependencies,
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
