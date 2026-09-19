from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "governance" / "PROJECT_STATE.json"


def git(*args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=True,
    )
    return proc.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Append an HT-CN Project OS attempt record")
    parser.add_argument("--change", required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument(
        "--result",
        required=True,
        choices=["success", "failed", "blocked", "cancelled"],
    )
    parser.add_argument("--summary", required=True)
    parser.add_argument("--decision", default="")
    parser.add_argument("--attempt-id", default="")
    args = parser.parse_args()

    state = json.loads(STATE.read_text(encoding="utf-8"))
    active = state.get("current", {}).get("active_change")
    if args.change != active:
        raise SystemExit(
            f"refuse attempt for non-active change: requested={args.change} active={active}"
        )

    now = datetime.now().astimezone()
    attempt_id = args.attempt_id or (
        f"A-{now:%Y%m%d-%H%M%S}-{args.change.replace('CR-', '')}"
    )
    record = {
        "attempt_id": attempt_id,
        "change_id": args.change,
        "recorded_at": now.isoformat(timespec="seconds"),
        "head": git("rev-parse", "HEAD"),
        "branch": git("branch", "--show-current") or "(detached)",
        "stage": args.stage,
        "result": args.result,
        "summary": args.summary,
    }
    if args.decision:
        record["decision"] = args.decision

    target = ROOT / state["ledgers"]["attempts"]
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    print(f"[HT-CN PROJECT OS] attempt appended: {attempt_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
