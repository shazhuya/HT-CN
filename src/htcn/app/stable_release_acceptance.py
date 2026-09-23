from __future__ import annotations

import json
import tomllib
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

EXPECTED_ENTRYPOINTS = (
    "启动HT-CN.bat",
    "停止HT-CN.bat",
    "安装HT-CN.bat",
    "更新HT-CN.bat",
    "备份HT-CN.bat",
    "恢复HT-CN.bat",
)
EXPECTED_DOCS = (
    "OPERATOR_GUIDE.md",
    "RECOVERY_CONTRACT.md",
)
ACTIVE_CHANGE = "CR-0084"
ACTIVE_SPEC = "specs/m9-phase-6-stable-product-release-acceptance.md"


@dataclass(frozen=True, slots=True)
class StableReleaseCheck:
    name: str
    passed: bool
    detail: str

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"JSON object required: {path}")
    return payload


def _project_version(root: Path) -> str:
    payload = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    value = str((payload.get("project") or {}).get("version") or "").strip()
    if not value:
        raise ValueError("project.version missing from pyproject.toml")
    return value


def _find_issue(payload: Mapping[str, Any], issue_id: str) -> dict[str, Any]:
    for row in payload.get("issues") or []:
        if isinstance(row, dict) and row.get("id") == issue_id:
            return row
    return {}


def _m9_phase_statuses(payload: Mapping[str, Any]) -> dict[str, str]:
    for milestone in payload.get("milestones") or []:
        if not isinstance(milestone, dict) or milestone.get("id") != "M9":
            continue
        return {
            str(row.get("id")): str(row.get("status"))
            for row in milestone.get("phases") or []
            if isinstance(row, dict) and row.get("id")
        }
    return {}


def evaluate_stable_release_acceptance(
    root: str | Path,
    *,
    release_report: Mapping[str, Any] | None = None,
) -> dict[str, object]:
    base = Path(root)
    state = _load_json(base / "governance/PROJECT_STATE.json")
    policy = _load_json(base / "governance/PRODUCT_COMPLETION_POLICY.json")
    issues = _load_json(base / "governance/OPEN_ISSUES.json")
    milestones = _load_json(base / "governance/MILESTONES.json")
    stable_release = _load_json(base / "governance/STABLE_RELEASE.json")
    report = (
        dict(release_report)
        if release_report is not None
        else _load_json(base / "artifacts/reports/m9-release-package.json")
    )

    checks: list[StableReleaseCheck] = []

    def add(name: str, passed: bool, detail: str) -> None:
        checks.append(StableReleaseCheck(name=name, passed=bool(passed), detail=detail))

    version = _project_version(base)
    current = state.get("current") or {}
    current_status = str(current.get("status") or "")
    add(
        "m9_6_state",
        current.get("milestone") == "M9"
        and current.get("phase") == "M9.6"
        and current_status in {"implementing", "validation_green", "ready_to_merge", "closed"},
        f"phase={current.get('phase')} status={current_status}",
    )
    if current_status == "closed":
        add(
            "closed_state_has_no_active_change",
            current.get("active_change") is None and current.get("active_spec") is None,
            f"change={current.get('active_change')} spec={current.get('active_spec')}",
        )
    else:
        add(
            "active_m9_6_change",
            current.get("active_change") == ACTIVE_CHANGE
            and current.get("active_spec") == ACTIVE_SPEC,
            f"change={current.get('active_change')} spec={current.get('active_spec')}",
        )

    phase_statuses = _m9_phase_statuses(milestones)
    add(
        "m9_1_to_m9_5_closed",
        all(phase_statuses.get(f"M9.{index}") == "closed" for index in range(1, 6)),
        json.dumps(phase_statuses, ensure_ascii=False, sort_keys=True),
    )
    add(
        "m9_6_milestone_active",
        phase_statuses.get("M9.6")
        in {"implementing", "validation_green", "ready_to_merge", "closed"},
        f"M9.6={phase_statuses.get('M9.6')}",
    )

    stable_definition = policy.get("stable_product_release_definition") or {}
    add(
        "product_completion_policy",
        stable_definition.get("requires_issue_0066_closed") is False
        and stable_definition.get("requires_user_daily_cli") is False
        and stable_definition.get("requires_daily_zip_handoff") is False
        and stable_definition.get("requires_automated_data_update") is True
        and stable_definition.get("requires_automated_harmonic_analysis") is True
        and stable_definition.get("requires_interactive_product_workbench") is True
        and stable_definition.get("requires_background_evidence_service") is True
        and stable_definition.get("requires_reliability_and_recovery") is True
        and stable_definition.get("requires_zero_cli_daily_operation") is True
        and stable_definition.get("requires_formal_release_gates") is True,
        "Stable Product policy preserves M9/M7/M8 separation and zero-CLI operation.",
    )

    issue_0066 = _find_issue(issues, "ISSUE-0066")
    issue_blocks = {str(value) for value in issue_0066.get("blocks") or []}
    add(
        "issue_0066_claims_only",
        issue_0066.get("status") in {"open", "closed"}
        and not any("M9" in value or "product release" in value.lower() for value in issue_blocks),
        f"status={issue_0066.get('status')} blocks={sorted(issue_blocks)}",
    )

    add(
        "stable_release_identity",
        stable_release.get("release_version") == version
        and stable_release.get("channel") == "stable"
        and stable_release.get("phase") == "M9.6"
        and stable_release.get("status") in {"candidate", "released"},
        f"manifest={stable_release.get('release_version')} project={version}",
    )

    verification = report.get("verification") or {}
    packaged_runtime = report.get("packaged_runtime_validation") or {}
    add(
        "verified_release_package",
        report.get("status") == "built"
        and report.get("release_version") == version
        and verification.get("verified") is True
        and packaged_runtime.get("status") == "success"
        and report.get("private_market_data_included") is False
        and report.get("mutable_data_included") is False,
        f"status={report.get('status')} version={report.get('release_version')} "
        f"verified={verification.get('verified')} runtime={packaged_runtime.get('status')}",
    )

    package_checks = packaged_runtime.get("checks") or {}
    add(
        "packaged_freeze_and_preflight",
        all(
            isinstance(package_checks.get(name), dict)
            and package_checks[name].get("exit_code") == 0
            for name in ("m4_methodology", "m4_outcome_engine", "product_preflight")
        ),
        "Packaged no-Git runtime must pass M4 37/4 guards and supervisor preflight.",
    )

    missing_entrypoints = [name for name in EXPECTED_ENTRYPOINTS if not (base / name).is_file()]
    add(
        "zero_cli_entrypoints",
        not missing_entrypoints,
        "missing=" + ",".join(missing_entrypoints),
    )

    missing_docs = [name for name in EXPECTED_DOCS if not (base / name).is_file()]
    add("operator_and_recovery_docs", not missing_docs, "missing=" + ",".join(missing_docs))
    if not missing_docs:
        operator_text = (base / "OPERATOR_GUIDE.md").read_text(encoding="utf-8")
        recovery_text = (base / "RECOVERY_CONTRACT.md").read_text(encoding="utf-8")
        add(
            "operator_contract_content",
            all(
                token in operator_text
                for token in ("无需命令行", "ISSUE-0066", "不执行证券交易")
            )
            and all(
                token in recovery_text
                for token in ("备份", "恢复", "回滚", "用户电脑")
            ),
            "Operator/recovery docs retain zero-CLI, claims-only and bounded recovery rules.",
        )

    accepted = all(item.passed for item in checks)
    return {
        "schema_version": 1,
        "phase": "M9.6",
        "status": "accepted" if accepted else "rejected",
        "accepted": accepted,
        "release_version": version,
        "release_head": report.get("release_head"),
        "package_sha256": report.get("package_sha256"),
        "issue_0066_status": issue_0066.get("status"),
        "statistical_claims_unlocked_by_this_acceptance": False,
        "user_computer_required": False,
        "is_trade_instruction": False,
        "checks": [item.as_payload() for item in checks],
    }
