from __future__ import annotations

from datetime import datetime, timezone
import json
import os
from pathlib import Path

from htcn.app.daily_review_digest import (
    build_latest_daily_review_digest,
)


ROOT = Path(__file__).resolve().parents[1]
HISTORY_ROOT = ROOT / "data" / "product" / "m5" / "operator_history"
REPORT_PATH = ROOT / "artifacts" / "reports" / "m5-daily-review-digest.json"


def _write_atomic(payload: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = REPORT_PATH.with_name(
        f".{REPORT_PATH.name}.{os.getpid()}.tmp"
    )
    data = (
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")
    with temp.open("wb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp, REPORT_PATH)


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        digest = build_latest_daily_review_digest(
            history_root=str(HISTORY_ROOT),
        )
        payload = {
            **digest,
            "generated_at_utc": generated_at,
            "history_root": str(HISTORY_ROOT.relative_to(ROOT)),
            "report_path": str(REPORT_PATH.relative_to(ROOT)),
        }
        code = 0 if payload.get("review_ready") else 2
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "generated_at_utc": generated_at,
            "status": "failed",
            "review_ready": False,
            "error": f"{type(exc).__name__}:{exc}",
            "history_root": str(HISTORY_ROOT.relative_to(ROOT)),
            "report_path": str(REPORT_PATH.relative_to(ROOT)),
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "historical_outcome_used_for_ranking": False,
            "predictive_score_used": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        }
        code = 2

    _write_atomic(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
