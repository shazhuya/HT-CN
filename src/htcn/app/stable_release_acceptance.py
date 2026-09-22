from __future__ import annotations

import json
import tomllib
import zipfile
from pathlib import Path
from typing import Any

from htcn.version import HTCN_VERSION

REQUIRED_DOCS = (
    "docs/OPERATOR_RUNBOOK.md",
    "docs/RECOVERY_CONTRACT.md",
    "docs/RELEASE_NOTES_v1.0.0.md",
)
REQUIRED_ENTRYPOINTS = (
    "安装HT-CN.bat",
    "启动HT-CN.bat",
    "停止HT-CN.bat",
    "更新HT-CN.bat",
    "备份HT-CN.bat",
    "恢复HT-CN.bat",
)
REQUIRED_PACKAGED_MEMBERS = (
    "governance/STABLE_PRODUCT_CONTRACT.json",
    *REQUIRED_DOCS,
)


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"{path} must contain a JSON object")
    return payload


def _project_version(root: Path) -> str:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    return str((payload.get("project") or {}).get("version") or "").strip()


def _issue(issues: dict[str, Any], issue_id: str) -> dict[str, Any] | None:
    for row in issues.get("issues") or []:
        if isinstance(row, dict) and row.get("id") == issue_id:
            return row
    return None


def evaluate_stable_release_acceptance(
    *,
    root: str | Path,
    release_report_path: str | Path,
) -> dict[str, Any]:
    base = Path(root)
    errors: list[str] = []
    contract = _read_json(base / "governance/STABLE_PRODUCT_CONTRACT.json")
    policy = _read_json(base / "governance/PRODUCT_COMPLETION_POLICY.json")
    milestones = _read_json(base / "governance/MILESTONES.json")
    issues = _read_json(base / "governance/OPEN_ISSUES.json")
    release = _read_json(Path(release_report_path))

    stable_version = str(contract.get("stable_version") or "")
    if stable_version != HTCN_VERSION:
        errors.append("stable_contract_version_mismatch")
    if _project_version(base) != HTCN_VERSION:
        errors.append("project_version_mismatch")
    if release.get("release_version") != HTCN_VERSION:
        errors.append("release_package_version_mismatch")

    m9 = next(
        (
            row
            for row in milestones.get("milestones") or []
            if isinstance(row, dict) and row.get("id") == "M9"
        ),
        None,
    )
    phases = [] if not isinstance(m9, dict) else [
        row for row in m9.get("phases") or [] if isinstance(row, dict)
    ]
    if not isinstance(m9, dict):
        errors.append("m9_milestone_missing")
    phase_status = {str(row.get("id")): str(row.get("status")) for row in phases}
    for phase in ("M9.0", "M9.1", "M9.2", "M9.3", "M9.4", "M9.5"):
        if phase_status.get(phase) != "closed":
            errors.append(f"product_phase_not_closed:{phase}")
    if phase_status.get("M9.6") not in {
        "planned", "ready_not_started", "implementing", "ready_to_merge", "closed"
    }:
        errors.append("m9_6_state_invalid")

    definition = policy.get("stable_product_release_definition")
    if not isinstance(definition, dict):
        errors.append("stable_product_release_definition_missing")
    else:
        for key in (
            "requires_automated_data_update",
            "requires_automated_harmonic_analysis",
            "requires_interactive_product_workbench",
            "requires_background_evidence_service",
            "requires_reliability_and_recovery",
            "requires_zero_cli_daily_operation",
            "requires_formal_release_gates",
            "post_release_evidence_continues",
        ):
            if definition.get(key) is not True:
                errors.append(f"stable_policy_not_enabled:{key}")
        for key in (
            "requires_issue_0066_closed",
            "requires_user_daily_cli",
            "requires_daily_zip_handoff",
        ):
            if definition.get(key) is not False:
                errors.append(f"stable_policy_boundary_invalid:{key}")

    caps = contract.get("product_capabilities")
    if not isinstance(caps, dict):
        errors.append("stable_product_capabilities_missing")
    else:
        for key in (
            "automated_market_data",
            "automated_harmonic_analysis",
            "interactive_product_workbench",
            "background_prospective_evidence",
            "reliability_and_recovery",
            "zero_cli_daily_operation",
        ):
            if caps.get(key) is not True:
                errors.append(f"stable_capability_missing:{key}")
        if caps.get("automatic_trading") is not False:
            errors.append("automatic_trading_must_remain_disabled")

    evidence = contract.get("evidence_boundary")
    if not isinstance(evidence, dict):
        errors.append("stable_evidence_boundary_missing")
    else:
        for key in (
            "statistical_features_available",
            "win_rate_claims_available",
            "alpha_claims_available",
            "profitability_claims_available",
            "statistical_significance_claims_available",
            "evidence_based_calibration_available",
        ):
            if evidence.get(key) is not False:
                errors.append(f"statistical_claim_surface_must_be_unavailable:{key}")
        if evidence.get("issue_id") != "ISSUE-0066":
            errors.append("stable_evidence_issue_mismatch")
        if evidence.get("blocks_product_release") is not False:
            errors.append("issue_0066_must_not_block_stable_release")

    issue_0066 = _issue(issues, "ISSUE-0066")
    if issue_0066 is None:
        errors.append("issue_0066_missing")
    elif issue_0066.get("status") not in {"open", "closed"}:
        errors.append("issue_0066_status_invalid")

    verification = release.get("verification")
    if not isinstance(verification, dict) or verification.get("verified") is not True:
        errors.append("release_package_not_verified")
    runtime = release.get("packaged_runtime_validation")
    if not isinstance(runtime, dict):
        errors.append("packaged_runtime_validation_missing")
    else:
        if runtime.get("status") != "success":
            errors.append("packaged_runtime_validation_failed")
        if runtime.get("git_present") is not False:
            errors.append("packaged_runtime_must_not_require_git")
        checks = runtime.get("checks")
        if not isinstance(checks, dict):
            errors.append("packaged_runtime_checks_missing")
        else:
            for name in ("m4_methodology", "m4_outcome_engine", "product_preflight"):
                row = checks.get(name)
                if not isinstance(row, dict) or row.get("exit_code") != 0:
                    errors.append(f"packaged_runtime_check_failed:{name}")

    if release.get("private_market_data_included") is not False:
        errors.append("release_contains_private_market_data")
    if release.get("mutable_data_included") is not False:
        errors.append("release_contains_mutable_data")

    for relative in (*REQUIRED_DOCS, *REQUIRED_ENTRYPOINTS):
        if not (base / relative).is_file():
            errors.append(f"required_release_file_missing:{relative}")

    package_path = Path(str(release.get("package_path") or ""))
    if not package_path.is_absolute():
        package_path = base / package_path
    if not package_path.is_file():
        errors.append("release_package_file_missing")
    else:
        with zipfile.ZipFile(package_path, "r") as archive:
            members = {info.filename for info in archive.infolist() if not info.is_dir()}
        for relative in REQUIRED_PACKAGED_MEMBERS:
            if relative not in members:
                errors.append(f"required_packaged_member_missing:{relative}")

    return {
        "schema_version": 1,
        "release_class": "stable_product",
        "stable_version": HTCN_VERSION,
        "status": "ready" if not errors else "blocked",
        "errors": errors,
        "issue_0066_status": None if issue_0066 is None else issue_0066.get("status"),
        "statistical_features_available": False,
        "automatic_trading": False,
        "m7_continues_in_background": True,
        "m8_requires_evidence_authorization": True,
        "release_head": release.get("release_head"),
        "release_package_sha256": release.get("package_sha256"),
    }


def write_stable_release_acceptance(
    *,
    root: str | Path,
    release_report_path: str | Path,
    output: str | Path,
) -> tuple[dict[str, Any], int]:
    payload = evaluate_stable_release_acceptance(
        root=root,
        release_report_path=release_report_path,
    )
    target = Path(output)
    if not target.is_absolute():
        target = Path(root) / target
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return payload, 0 if payload["status"] == "ready" else 2
