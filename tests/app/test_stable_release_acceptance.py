from __future__ import annotations

import json
import zipfile
from pathlib import Path

from htcn.app.stable_release_acceptance import evaluate_stable_release_acceptance


def _write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _fixture(tmp_path: Path) -> Path:
    (tmp_path / "pyproject.toml").write_text(
        '[project]\nname="ht-cn"\nversion="1.0.0"\n', encoding="utf-8"
    )
    _write(tmp_path / "governance/STABLE_PRODUCT_CONTRACT.json", {
        "stable_version": "1.0.0",
        "product_capabilities": {
            "automated_market_data": True,
            "automated_harmonic_analysis": True,
            "interactive_product_workbench": True,
            "background_prospective_evidence": True,
            "reliability_and_recovery": True,
            "zero_cli_daily_operation": True,
            "automatic_trading": False,
        },
        "evidence_boundary": {
            "issue_id": "ISSUE-0066",
            "blocks_product_release": False,
            "statistical_features_available": False,
            "win_rate_claims_available": False,
            "alpha_claims_available": False,
            "profitability_claims_available": False,
            "statistical_significance_claims_available": False,
            "evidence_based_calibration_available": False,
        },
    })
    _write(tmp_path / "governance/PRODUCT_COMPLETION_POLICY.json", {
        "stable_product_release_definition": {
            "requires_issue_0066_closed": False,
            "requires_user_daily_cli": False,
            "requires_daily_zip_handoff": False,
            "requires_automated_data_update": True,
            "requires_automated_harmonic_analysis": True,
            "requires_interactive_product_workbench": True,
            "requires_background_evidence_service": True,
            "requires_reliability_and_recovery": True,
            "requires_zero_cli_daily_operation": True,
            "requires_formal_release_gates": True,
            "post_release_evidence_continues": True,
        }
    })
    _write(tmp_path / "governance/MILESTONES.json", {
        "milestones": [{"id": "M9", "phases": [
            *[{"id": f"M9.{index}", "status": "closed"} for index in range(6)],
            {"id": "M9.6", "status": "implementing"},
        ]}]
    })
    _write(tmp_path / "governance/OPEN_ISSUES.json", {
        "issues": [{"id": "ISSUE-0066", "status": "open"}]
    })
    for relative in (
        "docs/OPERATOR_RUNBOOK.md", "docs/RECOVERY_CONTRACT.md",
        "docs/RELEASE_NOTES_v1.0.0.md", "安装HT-CN.bat", "启动HT-CN.bat",
        "停止HT-CN.bat", "更新HT-CN.bat", "备份HT-CN.bat", "恢复HT-CN.bat",
    ):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("ok\n", encoding="utf-8")
    package = tmp_path / "release.zip"
    with zipfile.ZipFile(package, "w") as archive:
        for relative in (
            "governance/STABLE_PRODUCT_CONTRACT.json",
            "docs/OPERATOR_RUNBOOK.md",
            "docs/RECOVERY_CONTRACT.md",
            "docs/RELEASE_NOTES_v1.0.0.md",
        ):
            archive.write(tmp_path / relative, relative)
    report = tmp_path / "release-report.json"
    _write(report, {
        "release_head": "a" * 40,
        "release_version": "1.0.0",
        "package_path": str(package),
        "package_sha256": "b" * 64,
        "private_market_data_included": False,
        "mutable_data_included": False,
        "verification": {"verified": True},
        "packaged_runtime_validation": {
            "status": "success", "git_present": False,
            "checks": {
                "m4_methodology": {"exit_code": 0},
                "m4_outcome_engine": {"exit_code": 0},
                "product_preflight": {"exit_code": 0},
            },
        },
    })
    return report


def test_stable_release_acceptance_allows_issue_0066_open(tmp_path) -> None:
    report = _fixture(tmp_path)
    payload = evaluate_stable_release_acceptance(root=tmp_path, release_report_path=report)
    assert payload["status"] == "ready"
    assert payload["issue_0066_status"] == "open"
    assert payload["statistical_features_available"] is False
    assert payload["automatic_trading"] is False


def test_stable_release_acceptance_rejects_statistical_claim_surface(tmp_path) -> None:
    report = _fixture(tmp_path)
    path = tmp_path / "governance/STABLE_PRODUCT_CONTRACT.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["evidence_boundary"]["win_rate_claims_available"] = True
    _write(path, payload)
    result = evaluate_stable_release_acceptance(root=tmp_path, release_report_path=report)
    assert result["status"] == "blocked"
    assert "statistical_claim_surface_must_be_unavailable:win_rate_claims_available" in result["errors"]


def test_stable_release_acceptance_rejects_release_version_drift(tmp_path) -> None:
    report = _fixture(tmp_path)
    payload = json.loads(report.read_text(encoding="utf-8"))
    payload["release_version"] = "0.9.0"
    _write(report, payload)
    result = evaluate_stable_release_acceptance(root=tmp_path, release_report_path=report)
    assert "release_package_version_mismatch" in result["errors"]
