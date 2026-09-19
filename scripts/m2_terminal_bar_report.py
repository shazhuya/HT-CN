from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "artifacts" / "ci-research" / "m2-autonomous-research-report.json"


def _rate(value) -> str:
    return "n/a" if value is None else f"{float(value):.4f}"


def main() -> int:
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    terminal = (payload.get("calibration") or {}).get("terminal_bar_calibration") or {}
    train = terminal.get("train") or {}
    validation = terminal.get("validation") or {}
    holdout = terminal.get("holdout") or {}
    counts = terminal.get("split_counts") or {}
    print(
        "[HT-CN M2 TBAR] "
        f"status={terminal.get('status')}, mature={terminal.get('mature_terminal_events', 0)}, "
        f"purged={terminal.get('purged_records', 0)}, "
        f"train={counts.get('train', 0)}, validation={counts.get('validation', 0)}, "
        f"holdout={counts.get('holdout', 0)} SEALED"
    )
    print(
        "[HT-CN M2 TBAR] TRAIN "
        f"T1={_rate(train.get('t1_rate'))}, T2={_rate(train.get('t2_rate'))}, "
        f"exit<=3={_rate(train.get('full_prz_exit_within_3_rate'))}, "
        f"exit<=5={_rate(train.get('full_prz_exit_within_5_rate'))}"
    )
    print(
        "[HT-CN M2 TBAR] VALIDATION "
        f"T1={_rate(validation.get('t1_rate'))}, T2={_rate(validation.get('t2_rate'))}, "
        f"exit<=3={_rate(validation.get('full_prz_exit_within_3_rate'))}, "
        f"exit<=5={_rate(validation.get('full_prz_exit_within_5_rate'))}"
    )
    print(
        "[HT-CN M2 TBAR] statuses="
        f"{json.dumps(terminal.get('terminal_bar_status_counts') or {}, ensure_ascii=False, sort_keys=True)}"
    )
    print(
        "[HT-CN M2 TBAR] confirmed_same_terminal train="
        f"{_rate(train.get('same_terminal_bar_later_confirmed_rate'))}, validation="
        f"{_rate(validation.get('same_terminal_bar_later_confirmed_rate'))}"
    )
    print(
        "[HT-CN M2 TBAR] HOLDOUT SEALED: outcome statistics intentionally not opened; "
        f"records={holdout.get('records', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
