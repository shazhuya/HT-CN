from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASELINE = ROOT / "governance" / "QUALITY_BASELINE.json"


def violation_budget(path: Path = BASELINE) -> int:
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("ruff", {}).get("violation_budget")
    if not isinstance(value, int) or value < 0:
        raise RuntimeError("ruff.violation_budget must be a non-negative integer")
    return value


def parse_violations(raw: str) -> list[dict[str, Any]]:
    payload = json.loads(raw)
    if not isinstance(payload, list) or any(not isinstance(row, dict) for row in payload):
        raise TypeError("ruff JSON output must be a list of objects")
    return payload


def main() -> int:
    proc = subprocess.run(
        [sys.executable, "-m", "ruff", "check", ".", "--output-format", "json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if proc.returncode not in {0, 1}:
        print(proc.stdout, end="")
        print(proc.stderr, end="", file=sys.stderr)
        return proc.returncode

    try:
        rows = parse_violations(proc.stdout)
    except (json.JSONDecodeError, TypeError) as exc:
        print(f"[HT-CN QUALITY] FATAL: cannot parse ruff output: {exc}", file=sys.stderr)
        return 2

    observed = len(rows)
    budget = violation_budget()
    print(f"[HT-CN QUALITY] ruff violations observed={observed} budget={budget}")
    if observed > budget:
        counts = Counter(str(row.get("code") or "UNKNOWN") for row in rows)
        summary = ", ".join(f"{code}={count}" for code, count in counts.most_common(12))
        print(f"[HT-CN QUALITY] top violations: {summary}", file=sys.stderr)
        for row in rows[:20]:
            location = row.get("location") or {}
            filename = row.get("filename") or "<unknown>"
            code = row.get("code") or "UNKNOWN"
            message = row.get("message") or ""
            row_number = location.get("row") or "?"
            column = location.get("column") or "?"
            print(
                f"[HT-CN QUALITY] {filename}:{row_number}:{column} {code} {message}",
                file=sys.stderr,
            )
            fix = row.get("fix")
            if fix:
                print(
                    "[HT-CN QUALITY] suggested_fix="
                    + json.dumps(fix, ensure_ascii=False, sort_keys=True),
                    file=sys.stderr,
                )
        print(
            "[HT-CN QUALITY] FATAL: lint debt increased; fix new violations or record an "
            "explicit CR before changing the baseline",
            file=sys.stderr,
        )
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
