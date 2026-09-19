from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path

from htcn.app.operator_history import (
    append_operator_history,
    query_operator_history,
)


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "artifacts" / "reports"
SOURCE_REPORT = REPORTS / "m5-operator-snapshot.json"
HISTORY_ROOT = ROOT / "data" / "product" / "m5" / "operator_history"
REPORT_PATH = REPORTS / "m5-operator-history.json"


def _write_report(payload: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )


def main() -> int:
    generated_at = datetime.now(timezone.utc).isoformat()
    try:
        appended = append_operator_history(
            root=ROOT,
            report_path=SOURCE_REPORT,
            history_root=HISTORY_ROOT,
        )
        recent = query_operator_history(
            history_root=HISTORY_ROOT,
            latest_revision_per_day=True,
            summary_only=True,
            limit=5,
        )
        payload = {
            "schema_version": 1,
            "generated_at_utc": generated_at,
            "status": "ready",
            "history_ready": True,
            "append_result": appended,
            "recent_history": recent,
            "history_root": str(HISTORY_ROOT.relative_to(ROOT)),
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "authoritative_transition": False,
            "historical_outcome_used_for_ranking": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        }
        code = 0
    except Exception as exc:
        payload = {
            "schema_version": 1,
            "generated_at_utc": generated_at,
            "status": "failed",
            "history_ready": False,
            "error": f"{type(exc).__name__}:{exc}",
            "history_root": str(HISTORY_ROOT.relative_to(ROOT)),
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "authoritative_transition": False,
            "historical_outcome_used_for_ranking": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        }
        code = 2

    _write_report(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
