from __future__ import annotations

import argparse
import json
import zipfile
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from htcn.app.evidence_identity import read_code_identity
from htcn.research.capture_transaction import read_committed_captures
from htcn.research.evidence_bundle import verify_evidence_bundle
from htcn.research.evidence_health import build_evidence_chain_health
from htcn.research.methodology_identity import build_methodology_identity
from htcn.research.outcome_engine_identity import (
    build_outcome_engine_identity,
)
from htcn.research.outcome_protocol import load_outcome_protocol
from htcn.research.outcome_snapshot import read_outcome_snapshots

BUNDLE_SCHEMA_VERSION = 1


def _sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _member(
    path: Path,
    *,
    arcname: str,
    required: bool,
) -> dict[str, Any]:
    return {
        "path": path,
        "arcname": arcname,
        "required": required,
    }


def build_bundle(
    *,
    transaction_root: Path,
    journal_path: Path,
    manifest_path: Path,
    reports_root: Path,
    output: Path,
    outcome_root: Path | None = None,
) -> dict[str, Any]:
    identity = read_code_identity()
    methodology = build_methodology_identity()
    outcome_engine = build_outcome_engine_identity()
    _, active_outcome_protocol = load_outcome_protocol()
    health = build_evidence_chain_health(
        transaction_root=transaction_root,
        journal_path=journal_path,
        manifest_path=manifest_path,
    )
    committed_read_error: str | None = None
    try:
        committed = read_committed_captures(transaction_root)
    except Exception as exc:
        committed = []
        committed_read_error = f"{type(exc).__name__}: {exc}"

    members: list[dict[str, Any]] = []

    for protocol_name, required in (
        ("m4-outcome-protocol-v1.json", False),
        ("m4-outcome-protocol-v2.json", True),
    ):
        outcome_protocol_path = Path("research") / protocol_name
        if outcome_protocol_path.is_file():
            members.append(
                _member(
                    outcome_protocol_path,
                    arcname=f"protocols/{protocol_name}",
                    required=required,
                )
            )
        elif required:
            members.append(
                _member(
                    outcome_protocol_path,
                    arcname=f"protocols/{protocol_name}",
                    required=True,
                )
            )

    outcome_snapshot_read_error: str | None = None
    outcome_snapshots: list[dict[str, Any]] = []
    if outcome_root is not None:
        try:
            outcome_snapshots = read_outcome_snapshots(outcome_root)
        except Exception as exc:
            outcome_snapshot_read_error = (
                f"{type(exc).__name__}: {exc}"
            )
        if outcome_root.exists():
            for path in sorted(
                outcome_root.glob("????-??-??__*.json")
            ):
                members.append(
                    _member(
                        path,
                        arcname=f"outcomes/{path.name}",
                        required=False,
                    )
                )

    baseline = transaction_root / "legacy_baseline.json"
    if baseline.is_file():
        members.append(
            _member(
                baseline,
                arcname="authoritative/legacy_baseline.json",
                required=True,
            )
        )

    for path in sorted(transaction_root.glob("????-??-??__*.json")):
        members.append(
            _member(
                path,
                arcname=f"authoritative/captures/{path.name}",
                required=True,
            )
        )

    report_names = (
        "m4-methodology-freeze-guard.json",
        "m4-outcome-engine-freeze-guard.json",
        "m4-m1-update.log",
        "m7-append-precheck.json",
        "m4-qfq-readiness.json",
        "m4-qfq-readiness.log",
        "m4-lifecycle-snapshot.json",
        "m4-evidence-health.json",
        "m4-evidence-health.md",
        "m4-lifecycle-transitions.json",
        "m4-lifecycle-transitions.md",
        "m4-prospective-observations.json",
        "m4-prospective-observations.md",
        "m4-outcome-v2.json",
        "m4-outcome-v2.md",
        "m7-accumulation-status.json",
        "m7-accumulation-status.md",
    )
    for name in report_names:
        path = reports_root / name
        if path.exists():
            members.append(
                _member(
                    path,
                    arcname=f"reports/{name}",
                    required=False,
                )
            )

    missing_required = [
        item["arcname"]
        for item in members
        if item["required"] and not item["path"].is_file()
    ]
    if missing_required:
        raise FileNotFoundError(
            f"required M4 evidence bundle member missing: {missing_required}"
        )

    file_records: list[dict[str, Any]] = []
    for item in members:
        path = Path(item["path"])
        if not path.is_file():
            continue
        file_records.append(
            {
                "arcname": str(item["arcname"]),
                "size_bytes": path.stat().st_size,
                "sha256": _sha256(path),
                "required": bool(item["required"]),
            }
        )

    latest_capture = committed[-1] if committed else None
    append_precheck: dict[str, Any] = {}
    precheck_path = reports_root / "m7-append-precheck.json"
    if precheck_path.is_file():
        try:
            value = json.loads(precheck_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                append_precheck = value
        except (OSError, json.JSONDecodeError):
            append_precheck = {}

    accumulation_status: dict[str, Any] = {}
    status_path = reports_root / "m7-accumulation-status.json"
    if status_path.is_file():
        try:
            value = json.loads(status_path.read_text(encoding="utf-8"))
            if isinstance(value, dict):
                accumulation_status = value
        except (OSError, json.JSONDecodeError):
            accumulation_status = {}

    manifest: dict[str, Any] = {
        "schema_version": BUNDLE_SCHEMA_VERSION,
        "status": (
            "evidence_health_blocked"
            if int(health.get("blocker_count") or 0) > 0
            else "transport_bundle_ready"
        ),
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "code_head": identity.head,
        "worktree_clean": identity.worktree_clean,
        "methodology_contract_version": methodology.contract_version,
        "methodology_fingerprint": methodology.fingerprint,
        "active_outcome_protocol_id": active_outcome_protocol.protocol_id,
        "active_outcome_protocol_fingerprint": (
            active_outcome_protocol.fingerprint
        ),
        "current_outcome_engine_contract_version": (
            outcome_engine.contract_version
        ),
        "current_outcome_engine_fingerprint": outcome_engine.fingerprint,
        "committed_capture_count": len(committed),
        "latest_committed_capture_date": (
            None
            if latest_capture is None
            else latest_capture.get("as_of_trade_date")
        ),
        "latest_capture_transaction_id": (
            None
            if latest_capture is None
            else latest_capture.get("transaction_id")
        ),
        "bundle_generation_code_head": identity.head,
        "bundle_generation_worktree_clean": identity.worktree_clean,
        "latest_capture_code_head": (
            None
            if latest_capture is None
            else latest_capture.get("code_head")
        ),
        "latest_capture_worktree_clean": (
            None
            if latest_capture is None
            else latest_capture.get("worktree_clean")
        ),
        "append_precheck_status": append_precheck.get("status"),
        "append_action": append_precheck.get("action"),
        "append_required": append_precheck.get("append_required"),
        "latest_closed_trade_date": append_precheck.get(
            "latest_closed_trade_date"
        ),
        "pending_closed_trade_count": append_precheck.get(
            "pending_closed_trade_count"
        ),
        "m7_accumulation_status": accumulation_status.get("status"),
        "m7_issue_gate": accumulation_status.get("issue_gate"),
        "evidence_health_status": health.get("status"),
        "evidence_health_blocker_count": health.get("blocker_count"),
        "committed_capture_read_error": committed_read_error,
        "outcome_snapshot_count": len(outcome_snapshots),
        "latest_outcome_as_of_trade_date": (
            None
            if not outcome_snapshots
            else outcome_snapshots[-1].get(
                "outcome_as_of_trade_date"
            )
        ),
        "latest_outcome_snapshot_id": (
            None
            if not outcome_snapshots
            else outcome_snapshots[-1].get("snapshot_id")
        ),
        "latest_outcome_engine_contract_version": (
            None
            if not outcome_snapshots
            else outcome_snapshots[-1].get(
                "outcome_engine_contract_version"
            )
        ),
        "latest_outcome_engine_fingerprint": (
            None
            if not outcome_snapshots
            else outcome_snapshots[-1].get(
                "outcome_engine_fingerprint"
            )
        ),
        "outcome_snapshot_read_error": outcome_snapshot_read_error,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
        "authoritative_evidence_modified": False,
        "interpretation": (
            "This ZIP is a transport bundle only. code_head identifies the "
            "bundle-generation checkout; latest_capture_code_head preserves the "
            "immutable origin of the latest committed capture. Enrollment "
            "authority remains the frozen baseline plus immutable committed "
            "capture transactions. Outcome snapshots are separate immutable "
            "derived research evidence."
        ),
        "files": file_records,
    }

    output.parent.mkdir(parents=True, exist_ok=True)
    tmp = output.with_name(f".{output.name}.tmp")
    if tmp.exists():
        tmp.unlink()

    with zipfile.ZipFile(
        tmp,
        mode="w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.writestr(
            "bundle-manifest.json",
            json.dumps(
                manifest,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
        )
        for item in members:
            path = Path(item["path"])
            if path.is_file():
                archive.write(path, arcname=str(item["arcname"]))

    verification = verify_evidence_bundle(tmp)
    if verification.status != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "M4 evidence transport bundle failed integrity verification: "
            + "; ".join(verification.errors)
        )

    tmp.replace(output)
    verification = verify_evidence_bundle(output)
    if verification.status != "valid":
        raise RuntimeError(
            "M4 evidence transport bundle changed after atomic replace: "
            + "; ".join(verification.errors)
        )

    return {
        **manifest,
        "output": str(output),
        "bundle_size_bytes": output.stat().st_size,
        "bundle_sha256": _sha256(output),
        "transport_verification": verification.as_payload(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Package M4 authoritative evidence and derived reports for handoff."
    )
    parser.add_argument(
        "--transaction-root",
        default="data/research/m4/captures",
    )
    parser.add_argument(
        "--journal",
        default="data/research/m4/lifecycle_journal.jsonl",
    )
    parser.add_argument(
        "--manifest",
        default="data/research/m4/snapshot_manifest.jsonl",
    )
    parser.add_argument(
        "--reports-root",
        default="artifacts/reports",
    )
    parser.add_argument(
        "--outcome-root",
        default="data/research/m4/outcomes",
    )
    parser.add_argument(
        "--output",
        default="artifacts/reports/m4-evidence-bundle.zip",
    )
    args = parser.parse_args()

    payload = build_bundle(
        transaction_root=Path(args.transaction_root),
        journal_path=Path(args.journal),
        manifest_path=Path(args.manifest),
        reports_root=Path(args.reports_root),
        output=Path(args.output),
        outcome_root=Path(args.outcome_root),
    )
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\n[M4] evidence transport bundle: {payload['output']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
