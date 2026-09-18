from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
from typing import Any
import zipfile

from htcn.research.evidence_bundle import verify_evidence_bundle


DAILY_HANDOFF_SCHEMA_VERSION = 1
CANONICAL_BARS = 420
CANONICAL_SCALES = (3, 5, 8, 13)


def _sha256_bytes(data: bytes) -> str:
    return sha256(data).hexdigest()


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_product_snapshots(
    cache_root: Path,
    *,
    limit: int = 2,
) -> list[Path]:
    by_date: dict[str, tuple[str, Path]] = {}
    if not cache_root.exists():
        return []

    for path in sorted(cache_root.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(payload, dict):
            continue
        if int(payload.get("bars") or 0) != CANONICAL_BARS:
            continue
        if tuple(int(v) for v in (payload.get("scales") or [])) != CANONICAL_SCALES:
            continue
        trade_date = str(payload.get("expected_trade_date") or "")
        if not trade_date:
            continue
        generated = str(payload.get("generated_at_utc") or "")
        previous = by_date.get(trade_date)
        if previous is None or generated >= previous[0]:
            by_date[trade_date] = (generated, path)

    dates = sorted(by_date, reverse=True)[:limit]
    return [by_date[date][1] for date in dates]


def verify_daily_handoff_bundle(path: str | Path) -> dict[str, Any]:
    bundle = Path(path)
    errors: list[str] = []
    manifest: dict[str, Any] | None = None

    if not bundle.is_file():
        return {
            "status": "invalid",
            "errors": ["bundle_missing"],
            "file_count": 0,
        }

    try:
        with zipfile.ZipFile(bundle, "r") as archive:
            names = archive.namelist()
            if len(names) != len(set(names)):
                errors.append("duplicate_archive_member")
            if "daily-handoff-manifest.json" not in names:
                errors.append("manifest_missing")
            else:
                raw = archive.read("daily-handoff-manifest.json")
                loaded = json.loads(raw.decode("utf-8"))
                if not isinstance(loaded, dict):
                    errors.append("manifest_not_object")
                else:
                    manifest = loaded

            if manifest is not None:
                listed = {
                    str(item.get("arcname")): item
                    for item in (manifest.get("files") or [])
                    if isinstance(item, dict) and item.get("arcname")
                }
                actual = set(names) - {"daily-handoff-manifest.json"}
                if set(listed) != actual:
                    errors.append("manifest_member_set_mismatch")
                for arcname, record in listed.items():
                    try:
                        data = archive.read(arcname)
                    except KeyError:
                        errors.append(f"member_missing:{arcname}")
                        continue
                    if len(data) != int(record.get("size_bytes") or -1):
                        errors.append(f"member_size_mismatch:{arcname}")
                    if _sha256_bytes(data) != str(record.get("sha256") or ""):
                        errors.append(f"member_hash_mismatch:{arcname}")
    except Exception as exc:
        errors.append(f"zip_read_error:{type(exc).__name__}:{exc}")

    return {
        "status": "valid" if not errors else "invalid",
        "errors": errors,
        "file_count": (
            0 if manifest is None else len(manifest.get("files") or [])
        ),
        "manifest": manifest,
    }


def build_daily_handoff_bundle(
    *,
    root: str | Path,
    pipeline_summary: dict[str, Any],
    output: str | Path,
) -> dict[str, Any]:
    repo = Path(root)
    output_path = Path(output)
    if not output_path.is_absolute():
        output_path = repo / output_path

    reports = repo / "artifacts" / "reports"
    cache_root = repo / "data" / "product" / "m5" / "operator_queue"

    members: list[tuple[str, bytes, str]] = []
    product_ready = bool(pipeline_summary.get("m5_product_ready"))
    research_ready = bool(pipeline_summary.get("m4_research_ready"))
    pipeline_bytes = _canonical_json_bytes(pipeline_summary)
    members.append((
        "pipeline/m5-daily-close-pipeline.json",
        pipeline_bytes,
        "pipeline_summary",
    ))

    m5_report = reports / "m5-operator-snapshot.json"
    if m5_report.is_file():
        members.append((
            "m5/m5-operator-snapshot.json",
            m5_report.read_bytes(),
            "m5_product_summary",
        ))

    snapshots = _canonical_product_snapshots(cache_root, limit=2)
    for index, path in enumerate(snapshots):
        if product_ready:
            role = (
                "m5_current_product_snapshot"
                if index == 0
                else "m5_previous_product_snapshot"
            )
        else:
            role = "m5_existing_product_snapshot"
        members.append((
            f"m5/operator_snapshots/{path.name}",
            path.read_bytes(),
            role,
        ))

    for path in sorted(reports.glob("m5-daily-*.log")):
        members.append((
            f"logs/{path.name}",
            path.read_bytes(),
            "pipeline_step_log",
        ))

    m4_bundle = reports / "m4-evidence-bundle.zip"
    m4_verification: dict[str, Any] | None = None
    if m4_bundle.is_file():
        checked = verify_evidence_bundle(m4_bundle)
        m4_verification = checked.as_payload()
        if checked.status != "valid":
            raise RuntimeError(
                "nested M4 evidence bundle is invalid: "
                + "; ".join(checked.errors)
            )
        members.append((
            "m4/m4-evidence-bundle.zip",
            m4_bundle.read_bytes(),
            (
                "m4_evidence_transport_bundle"
                if research_ready
                else "m4_existing_evidence_transport_bundle"
            ),
        ))

    current_snapshot_count = sum(
        1 for _, _, role in members
        if role == "m5_current_product_snapshot"
    )
    m4_bundle_count = sum(
        1 for _, _, role in members
        if role == "m4_evidence_transport_bundle"
    )

    blockers: list[str] = []
    if product_ready and current_snapshot_count != 1:
        blockers.append("product_ready_but_current_snapshot_missing")
    if research_ready and m4_bundle_count != 1:
        blockers.append("research_ready_but_m4_bundle_missing")
    if blockers:
        raise RuntimeError("daily handoff requirements failed: " + "; ".join(blockers))

    records = [
        {
            "arcname": arcname,
            "role": role,
            "size_bytes": len(data),
            "sha256": _sha256_bytes(data),
        }
        for arcname, data, role in members
    ]
    manifest = {
        "schema_version": DAILY_HANDOFF_SCHEMA_VERSION,
        "status": (
            "complete_transport"
            if product_ready and research_ready
            else "partial_transport"
        ),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "transport_only": True,
        "authoritative_evidence": False,
        "m4_authority_remains_nested_capture_chain": True,
        "m5_product_snapshots_are_authoritative_evidence": False,
        "pipeline_overall_status": pipeline_summary.get("overall_status"),
        "data_ready": pipeline_summary.get("data_ready"),
        "m5_product_ready": product_ready,
        "m4_research_ready": research_ready,
        "m5_snapshot_count": len(snapshots),
        "m4_nested_bundle_verification": m4_verification,
        "files": records,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = output_path.with_name(f".{output_path.name}.tmp")
    tmp.unlink(missing_ok=True)

    with zipfile.ZipFile(
        tmp,
        "w",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        archive.writestr(
            "daily-handoff-manifest.json",
            _canonical_json_bytes(manifest),
        )
        for arcname, data, _ in members:
            archive.writestr(arcname, data)

    verification = verify_daily_handoff_bundle(tmp)
    if verification["status"] != "valid":
        tmp.unlink(missing_ok=True)
        raise RuntimeError(
            "daily handoff bundle verification failed: "
            + "; ".join(verification["errors"])
        )
    tmp.replace(output_path)

    final_verification = verify_daily_handoff_bundle(output_path)
    if final_verification["status"] != "valid":
        raise RuntimeError("daily handoff changed after atomic replace")

    return {
        **manifest,
        "output": str(output_path),
        "bundle_size_bytes": output_path.stat().st_size,
        "bundle_sha256": _sha256_path(output_path),
        "verification": {
            "status": final_verification["status"],
            "errors": final_verification["errors"],
            "file_count": final_verification["file_count"],
        },
    }
