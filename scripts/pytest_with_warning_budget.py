from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Iterable
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "governance" / "QUALITY_BASELINE.json"
WARNING_RE = re.compile(r"(?<!\d)(\d+) warnings?\b")


def parse_warning_count(lines: Iterable[str]) -> int:
    counts: list[int] = []
    for line in lines:
        counts.extend(int(value) for value in WARNING_RE.findall(line))
    return max(counts, default=0)


def warning_budget(path: Path = BASELINE) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("pytest", {}).get("warning_budget")
    if not isinstance(value, int) or value < 0:
        raise RuntimeError("pytest.warning_budget must be a non-negative integer")
    return value


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run pytest and fail when the frozen warning budget increases"
    )
    parser.add_argument("pytest_args", nargs=argparse.REMAINDER)
    args = parser.parse_args()

    command = [sys.executable, "-m", "pytest", "-q", *args.pytest_args]
    proc = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert proc.stdout is not None
    output: list[str] = []
    for line in proc.stdout:
        print(line, end="")
        output.append(line)
    return_code = proc.wait()
    if return_code != 0:
        return return_code

    observed = parse_warning_count(output)
    budget = warning_budget()
    print(f"[HT-CN QUALITY] pytest warnings observed={observed} budget={budget}")
    if observed > budget:
        print(
            "[HT-CN QUALITY] FATAL: warning budget increased; fix the new warnings or "
            "record an explicit CR before changing the baseline",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
