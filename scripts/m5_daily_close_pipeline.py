from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

from htcn.app.daily_close_pipeline import (
    DailyCloseStep,
    execute_daily_close_steps,
)
from htcn.app.daily_close_runner import evaluate_daily_close_preflight


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "artifacts" / "reports"
REPORT_PATH = REPORT_ROOT / "m5-daily-close-pipeline.json"
CATALOG_PATH = ROOT / "data" / "market" / "catalog.duckdb"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )


def _resolve_preflight():
    repository_available = (ROOT / ".git").exists()
    branch: str | None = None
    head: str | None = None
    porcelain = ""

    if repository_available:
        branch_result = _git(
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
        )
        if branch_result.returncode == 0:
            branch = branch_result.stdout.strip() or None

        head_result = _git("rev-parse", "HEAD")
        if head_result.returncode == 0:
            head = head_result.stdout.strip() or None

        status_result = _git("status", "--porcelain")
        if status_result.returncode == 0:
            porcelain = status_result.stdout
        else:
            porcelain = "__git_status_failed__"

    return evaluate_daily_close_preflight(
        branch=branch,
        head=head,
        porcelain=porcelain,
        repository_available=repository_available,
        catalog_available=CATALOG_PATH.is_file(),
    )


def _run_step(step: DailyCloseStep) -> int:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
    log_path = REPORT_ROOT / step.log_name
    command = [sys.executable, "-u", *step.command]

    print()
    print("=" * 76, flush=True)
    print(
        f"[HT-CN DAILY] START {step.name} "
        f"lane={step.lane}",
        flush=True,
    )
    print(" ".join(command), flush=True)
    print("=" * 76, flush=True)

    with log_path.open(
        "w",
        encoding="utf-8",
        newline="\n",
    ) as log:
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
        )
        assert process.stdout is not None
        for line in process.stdout:
            print(line, end="", flush=True)
            log.write(line)
            log.flush()
        code = int(process.wait())

    print(
        f"[HT-CN DAILY] END {step.name} exit={code}; "
        f"log={log_path.relative_to(ROOT)}",
        flush=True,
    )
    return code


def _write_report(payload: dict[str, object]) -> None:
    REPORT_ROOT.mkdir(parents=True, exist_ok=True)
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
    preflight = _resolve_preflight()

    if not preflight.product_lane_ready:
        payload: dict[str, object] = {
            "schema_version": 2,
            "generated_at_utc": generated_at,
            "overall_status": "failed_product_preflight",
            "exit_code": 2,
            "preflight": preflight.as_payload(),
            "steps": {},
            "market_data_ready": False,
            "m5_product_ready": False,
            "m5_context_refresh_ready": False,
            "m4_research_ready": False,
        }
        _write_report(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(
            f"[HT-CN DAILY] PRODUCT PRECHECK FAILED -> {REPORT_PATH}",
            flush=True,
        )
        return 2

    summary = execute_daily_close_steps(
        _run_step,
        research_preflight_ready=preflight.research_lane_ready,
        research_preflight_reason=(
            None
            if preflight.research_lane_ready
            else "m4_source_preflight_not_ready:"
            + ",".join(preflight.research_errors)
        ),
    )
    summary["generated_at_utc"] = generated_at
    summary["preflight"] = preflight.as_payload()
    summary["python_executable"] = sys.executable
    summary["artifacts"] = {
        "pipeline_report": str(REPORT_PATH.relative_to(ROOT)),
        "m5_operator_snapshot_report": (
            "artifacts/reports/m5-operator-snapshot.json"
        ),
        "m5_product_cache": "data/product/m5/operator_queue",
        "m5_operator_history_report": (
            "artifacts/reports/m5-operator-history.json"
        ),
        "m5_operator_history_root": (
            "data/product/m5/operator_history"
        ),
        "m5_daily_review_digest": (
            "artifacts/reports/m5-daily-review-digest.json"
        ),
        "m4_lifecycle_snapshot": (
            "artifacts/reports/m4-lifecycle-snapshot.json"
        ),
        "m4_evidence_health": (
            "artifacts/reports/m4-evidence-health.json"
        ),
        "m4_transition_report": (
            "artifacts/reports/m4-lifecycle-transitions.json"
        ),
        "m4_observation_report": (
            "artifacts/reports/m4-prospective-observations.json"
        ),
        "m4_outcome_report": "artifacts/reports/m4-outcome-v2.json",
        "m4_evidence_bundle": (
            "artifacts/reports/m4-evidence-bundle.zip"
        ),
    }
    _write_report(summary)

    print()
    print("=" * 76, flush=True)
    print("HT-CN DAILY CLOSE SUMMARY", flush=True)
    print(
        f"overall={summary['overall_status']} "
        f"market_data_ready={summary['market_data_ready']} "
        f"m5_product_ready={summary['m5_product_ready']} "
        f"context_refresh={summary['m5_context_refresh_ready']} "
        f"history_ready={summary['m5_history_ready']} "
        f"review_digest_ready={summary['m5_review_digest_ready']} "
        f"m4_research_ready={summary['m4_research_ready']}",
        flush=True,
    )
    if (
        summary["m5_product_ready"]
        and not summary["m5_history_ready"]
    ):
        print(
            "[HT-CN DAILY] M5 product is ready. "
            "Operator history is degraded independently.",
            flush=True,
        )
    if (
        summary["m5_product_ready"]
        and not summary["m5_review_digest_ready"]
    ):
        print(
            "[HT-CN DAILY] M5 product is ready. "
            "Daily review digest is degraded independently.",
            flush=True,
        )
    if (
        summary["m5_product_ready"]
        and not summary["m4_research_ready"]
    ):
        print(
            "[HT-CN DAILY] M5 product is ready. "
            "M4 research lane is degraded/blocked independently.",
            flush=True,
        )
    print(f"report={REPORT_PATH.relative_to(ROOT)}", flush=True)
    print("=" * 76, flush=True)
    return int(summary["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
