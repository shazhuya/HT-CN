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
from htcn.app.daily_handoff import build_daily_handoff_bundle


ROOT = Path(__file__).resolve().parents[1]
REPORT_ROOT = ROOT / "artifacts" / "reports"
REPORT_PATH = REPORT_ROOT / "m5-daily-close-pipeline.json"
HANDOFF_PATH = REPORT_ROOT / "htcn-daily-handoff.zip"
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


def _resolve_git_preflight():
    repository_available = (ROOT / ".git").exists()
    branch: str | None = None
    head: str | None = None
    porcelain = ""

    if repository_available:
        branch_result = _git("symbolic-ref", "--quiet", "--short", "HEAD")
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
    command = [sys.executable, *step.command]

    print()
    print("=" * 72)
    print(f"[HT-CN DAILY] {step.name}")
    print(" ".join(command))
    print("=" * 72)

    completed = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )
    output = completed.stdout or ""
    log_path.write_text(output, encoding="utf-8")
    if output:
        print(output, end="" if output.endswith("\n") else "\n")
    print(
        f"[HT-CN DAILY] {step.name} exit={completed.returncode}; "
        f"log={log_path.relative_to(ROOT)}"
    )
    return int(completed.returncode)


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
    preflight = _resolve_git_preflight()

    if not preflight.passed:
        payload: dict[str, object] = {
            "schema_version": 1,
            "generated_at_utc": generated_at,
            "overall_status": "failed_preflight",
            "exit_code": 2,
            "preflight": preflight.as_payload(),
            "steps": {},
            "data_ready": False,
            "m5_product_ready": False,
            "m4_research_ready": False,
            "boundaries": {
                "branch_name_owns_methodology_identity": False,
                "freeze_guards_own_cross_branch_capture_permission": True,
                "m5_cache_writes_m4_evidence": False,
            },
        }
        _write_report(payload)
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        print(f"[HT-CN DAILY] PRECHECK FAILED -> {REPORT_PATH}")
        return 2

    summary = execute_daily_close_steps(_run_step)
    summary["generated_at_utc"] = generated_at
    summary["preflight"] = preflight.as_payload()
    summary["python_executable"] = sys.executable
    summary["artifacts"] = {
        "pipeline_report": str(REPORT_PATH.relative_to(ROOT)),
        "daily_handoff_bundle": str(HANDOFF_PATH.relative_to(ROOT)),
        "m5_operator_snapshot_report": "artifacts/reports/m5-operator-snapshot.json",
        "m4_lifecycle_snapshot": "artifacts/reports/m4-lifecycle-snapshot.json",
        "m4_evidence_health": "artifacts/reports/m4-evidence-health.json",
        "m4_transition_report": "artifacts/reports/m4-lifecycle-transitions.json",
        "m4_observation_report": "artifacts/reports/m4-prospective-observations.json",
        "m4_outcome_report": "artifacts/reports/m4-outcome-v2.json",
        "m4_evidence_bundle": "artifacts/reports/m4-evidence-bundle.zip",
        "m4_authoritative_captures": "data/research/m4/captures",
        "m5_product_cache": "data/product/m5/operator_queue",
    }

    try:
        handoff = build_daily_handoff_bundle(
            root=ROOT,
            pipeline_summary=summary,
            output=HANDOFF_PATH,
        )
        summary["handoff_ready"] = True
        summary["daily_handoff"] = {
            "status": handoff.get("status"),
            "output": str(HANDOFF_PATH.relative_to(ROOT)),
            "bundle_size_bytes": handoff.get("bundle_size_bytes"),
            "bundle_sha256": handoff.get("bundle_sha256"),
            "verification": handoff.get("verification"),
        }
    except Exception as exc:
        summary["handoff_ready"] = False
        summary["daily_handoff"] = {
            "status": "failed",
            "output": str(HANDOFF_PATH.relative_to(ROOT)),
            "error": f"{type(exc).__name__}: {exc}",
        }
        if int(summary["exit_code"]) == 0:
            summary["exit_code"] = 1
            summary["overall_status"] = "partial"

    _write_report(summary)

    print()
    print("=" * 72)
    print("HT-CN DAILY CLOSE SUMMARY")
    print(
        f"overall={summary['overall_status']} "
        f"data_ready={summary['data_ready']} "
        f"m5_product_ready={summary['m5_product_ready']} "
        f"m4_research_ready={summary['m4_research_ready']} "
        f"handoff_ready={summary.get('handoff_ready', False)}"
    )
    print(f"report={REPORT_PATH.relative_to(ROOT)}")
    print(f"handoff={HANDOFF_PATH.relative_to(ROOT)}")
    print("=" * 72)
    return int(summary["exit_code"])


if __name__ == "__main__":
    raise SystemExit(main())
