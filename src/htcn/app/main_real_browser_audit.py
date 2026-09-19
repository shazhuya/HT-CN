from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
from typing import Any


BROWSER_SOURCE_SCHEMA_VERSION = 1
BROWSER_EVIDENCE_SCHEMA_VERSION = 1


@dataclass(frozen=True, slots=True)
class MainRealBrowserAuditContract:
    version: int = 1
    semantics: str = "browser_qa_over_latest_phase19_workspace"
    consumes_workspace_only: bool = True
    requires_network_fetch: bool = False
    browser_qa_is_m4_evidence: bool = False
    mutates_product_state: bool = False
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    mutates_source_lifecycle: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def _read_json_object(path: Path, *, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"{label}_unreadable:{type(exc).__name__}") from exc
    if not isinstance(value, dict):
        raise RuntimeError(f"{label}_not_object")
    return value


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    tmp.write_text(
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    tmp.replace(path)


def _copy_atomic(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f".{target.name}.tmp")
    tmp.unlink(missing_ok=True)
    shutil.copyfile(source, tmp)
    tmp.replace(target)


def _schema_counts(inspection: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    details = inspection.get("details_by_display_key")
    if not isinstance(details, dict):
        return counts
    for detail in details.values():
        if not isinstance(detail, dict):
            continue
        visual = detail.get("visual_semantics")
        visual = visual if isinstance(visual, dict) else {}
        schema = str(visual.get("schema") or "")
        if not schema:
            pattern = detail.get("pattern")
            pattern = pattern if isinstance(pattern, dict) else {}
            schema = str(pattern.get("schema") or "")
        if schema:
            counts[schema] = counts.get(schema, 0) + 1
    return dict(sorted(counts.items()))


def prepare_main_real_browser_source(
    *,
    root: str | Path,
    workspace_source: str | Path,
    inspection_source: str | Path,
    output_html: str | Path,
    source_report: str | Path,
    mode: str,
    trade_date: str,
    source_identity: str,
    structural_closeout_status: str | None = None,
    structural_closeout_report_sha256: str | None = None,
) -> dict[str, Any]:
    repo = Path(root).resolve()

    def resolve(value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = repo / path
        return path.resolve()

    workspace = resolve(workspace_source)
    inspection_path = resolve(inspection_source)
    html_output = resolve(output_html)
    report_output = resolve(source_report)

    if mode not in ("phase19_latest", "deterministic_fixture"):
        raise RuntimeError("browser_source_mode_invalid")
    if not workspace.is_file():
        raise RuntimeError("browser_workspace_missing")
    if not inspection_path.is_file():
        raise RuntimeError("browser_inspection_missing")

    inspection = _read_json_object(
        inspection_path,
        label="browser_inspection",
    )
    summary = inspection.get("summary")
    summary = summary if isinstance(summary, dict) else {}
    portable_items = inspection.get("portable_items")
    portable_items = portable_items if isinstance(portable_items, list) else []

    if mode == "phase19_latest":
        if structural_closeout_status not in ("ready", "ready_with_warnings"):
            raise RuntimeError("structural_closeout_not_ready")
        if not trade_date:
            raise RuntimeError("phase19_trade_date_missing")
        if len(source_identity) != 64:
            raise RuntimeError("phase19_bundle_sha_invalid")

    detail_available_count = sum(
        1
        for item in portable_items
        if isinstance(item, dict) and item.get("detail_available") is True
    )
    detail_error_count = sum(
        1
        for item in portable_items
        if isinstance(item, dict) and item.get("detail_available") is not True
    )

    _copy_atomic(workspace, html_output)
    payload = {
        "schema_version": BROWSER_SOURCE_SCHEMA_VERSION,
        "mode": mode,
        "trade_date": trade_date,
        "source_identity": source_identity,
        "workspace_source": str(workspace),
        "workspace_source_sha256": _sha256_path(workspace),
        "browser_workspace": str(html_output),
        "browser_workspace_sha256": _sha256_path(html_output),
        "inspection_source": str(inspection_path),
        "inspection_source_sha256": _sha256_path(inspection_path),
        "candidate_count": len(portable_items),
        "detail_available_count": detail_available_count,
        "detail_error_count": detail_error_count,
        "schema_counts": _schema_counts(inspection),
        "transport_status": summary.get("status"),
        "visual_semantics_version": int(
            (inspection.get("contract") or {}).get(
                "visual_semantics_version"
            )
            or 2
        )
        if isinstance(inspection.get("contract"), dict)
        else 2,
        "structural_closeout_status": structural_closeout_status,
        "structural_closeout_report_sha256": (
            structural_closeout_report_sha256
        ),
        "contract": MainRealBrowserAuditContract().as_payload(),
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
    }
    _write_json_atomic(report_output, payload)
    return payload


def verify_main_real_browser_evidence(
    *,
    root: str | Path,
    source_report: str | Path,
    evidence_report: str | Path,
) -> dict[str, Any]:
    repo = Path(root).resolve()

    def resolve(value: str | Path) -> Path:
        path = Path(value)
        if not path.is_absolute():
            path = repo / path
        return path.resolve()

    source_path = resolve(source_report)
    evidence_path = resolve(evidence_report)
    source = _read_json_object(source_path, label="browser_source_report")
    evidence = _read_json_object(
        evidence_path,
        label="browser_evidence_report",
    )

    errors: list[str] = []
    if int(source.get("schema_version") or 0) != BROWSER_SOURCE_SCHEMA_VERSION:
        errors.append("browser_source_schema_invalid")
    if int(evidence.get("schema_version") or 0) != BROWSER_EVIDENCE_SCHEMA_VERSION:
        errors.append("browser_evidence_schema_invalid")
    if evidence.get("phase") != "M5 Phase 21":
        errors.append("browser_evidence_phase_invalid")
    if evidence.get("browser") != "chromium":
        errors.append("browser_evidence_browser_invalid")

    for field in (
        "trade_date",
        "source_identity",
    ):
        if str(evidence.get(field) or "") != str(source.get(field) or ""):
            errors.append(f"browser_evidence_source_mismatch:{field}")

    for field in (
        "candidate_count",
        "detail_available_count",
        "detail_error_count",
    ):
        try:
            left = int(evidence.get(field))
            right = int(source.get(field))
        except (TypeError, ValueError):
            errors.append(f"browser_evidence_count_invalid:{field}")
        else:
            if left != right:
                errors.append(f"browser_evidence_count_mismatch:{field}")

    if dict(evidence.get("schema_counts") or {}) != dict(
        source.get("schema_counts") or {}
    ):
        errors.append("browser_evidence_schema_counts_mismatch")

    for evidence_field, source_field, error_code in (
        (
            "audited_detail_count",
            "detail_available_count",
            "browser_evidence_audited_detail_count_mismatch",
        ),
        (
            "explicit_error_count",
            "detail_error_count",
            "browser_evidence_explicit_error_count_mismatch",
        ),
    ):
        try:
            evidence_count = int(evidence.get(evidence_field))
            source_count = int(source.get(source_field))
        except (TypeError, ValueError):
            errors.append(
                f"browser_evidence_count_invalid:{evidence_field}"
            )
            continue
        if evidence_count != source_count:
            errors.append(error_code)
    zero_required_fields = (
        ("future_point_violation_count", "browser_evidence_future_point_violation"),
        ("page_error_count", "browser_evidence_page_errors"),
        ("console_error_count", "browser_evidence_console_errors"),
    )
    for field, error_code in zero_required_fields:
        try:
            value = int(evidence.get(field))
        except (TypeError, ValueError):
            errors.append(f"browser_evidence_count_invalid:{field}")
            continue
        if value != 0:
            errors.append(error_code)

    if evidence.get("all_detail_geometry_matches_semantics") is not True:
        errors.append("browser_evidence_geometry_not_exhaustive")
    if evidence.get("all_explicit_errors_rendered") is not True:
        errors.append("browser_evidence_explicit_errors_not_rendered")
    if evidence.get("layer_toggle_check_passed") is not True:
        errors.append("browser_evidence_layer_toggle_failed")
    if evidence.get("no_network_fetch_observed") is not True:
        errors.append("browser_evidence_network_fetch_observed")

    for field in (
        "writes_m4_evidence",
        "mutates_product_state",
        "mutates_harmonic_identity",
        "mutates_source_raw_prz",
        "mutates_source_lifecycle",
        "is_trade_instruction",
    ):
        if evidence.get(field) is not False:
            errors.append(f"browser_evidence_boundary_invalid:{field}")

    screenshots = evidence.get("screenshots")
    if not isinstance(screenshots, list) or not screenshots:
        errors.append("browser_evidence_screenshots_missing")
        screenshots = []
    for record in screenshots:
        if not isinstance(record, dict):
            errors.append("browser_evidence_screenshot_record_invalid")
            continue
        raw_path = str(record.get("file") or "")
        path = Path(raw_path)
        if not path.is_absolute():
            # Playwright executes from apps/web; support its ../../artifacts path.
            candidates = [
                (repo / "apps" / "web" / path).resolve(),
                (repo / path).resolve(),
            ]
            path = next(
                (candidate for candidate in candidates if candidate.is_file()),
                candidates[0],
            )
        if not path.is_file():
            errors.append(f"browser_evidence_screenshot_missing:{raw_path}")
            continue
        size = path.stat().st_size
        if size <= 10_000:
            errors.append(f"browser_evidence_screenshot_too_small:{path.name}")
        if int(record.get("size_bytes") or -1) != size:
            errors.append(f"browser_evidence_screenshot_size_mismatch:{path.name}")
        if str(record.get("sha256") or "") != _sha256_path(path):
            errors.append(f"browser_evidence_screenshot_hash_mismatch:{path.name}")

    status = "valid" if not errors else "invalid"
    return {
        "schema_version": 1,
        "status": status,
        "error_count": len(errors),
        "errors": errors,
        "trade_date": source.get("trade_date"),
        "source_identity": source.get("source_identity"),
        "candidate_count": source.get("candidate_count"),
        "detail_available_count": source.get("detail_available_count"),
        "detail_error_count": source.get("detail_error_count"),
        "schema_counts": source.get("schema_counts"),
        "screenshot_count": len(screenshots),
        "browser_evidence_is_m4_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
    }


def finalize_main_real_closeout(
    *,
    structural_report: dict[str, Any],
    browser_verification: dict[str, Any],
) -> dict[str, Any]:
    errors: list[str] = []
    warnings = list(structural_report.get("warnings") or [])
    if structural_report.get("status") not in ("ready", "ready_with_warnings"):
        errors.append("structural_closeout_invalid")
    if browser_verification.get("status") != "valid":
        errors.append("browser_closeout_invalid")
    if str(structural_report.get("trade_date") or "") != str(
        browser_verification.get("trade_date") or ""
    ):
        errors.append("closeout_trade_date_mismatch")
    if str(structural_report.get("bundle_sha256") or "") != str(
        browser_verification.get("source_identity") or ""
    ):
        errors.append("closeout_bundle_identity_mismatch")

    status = (
        "invalid"
        if errors
        else "ready_with_warnings"
        if warnings
        else "ready"
    )
    return {
        "schema_version": 1,
        "status": status,
        "full_closeout_ready": not errors,
        "trade_date": structural_report.get("trade_date"),
        "main_head": structural_report.get("current_head"),
        "bundle_sha256": structural_report.get("bundle_sha256"),
        "errors": errors,
        "warnings": warnings,
        "structural_status": structural_report.get("status"),
        "browser_status": browser_verification.get("status"),
        "browser_screenshot_count": browser_verification.get(
            "screenshot_count"
        ),
        "candidate_count": browser_verification.get("candidate_count"),
        "detail_available_count": browser_verification.get(
            "detail_available_count"
        ),
        "detail_error_count": browser_verification.get(
            "detail_error_count"
        ),
        "schema_counts": browser_verification.get("schema_counts"),
        "real_m1_required": True,
        "browser_qa_is_m4_evidence": False,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "is_trade_instruction": False,
    }
