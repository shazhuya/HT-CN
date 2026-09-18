from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import os
from typing import Any

from .capture_transaction import (
    committed_capture_view,
    frozen_legacy_baseline_present,
    frozen_legacy_baseline_through_date,
    read_committed_captures,
    read_frozen_legacy_baseline,
)


@dataclass(frozen=True, slots=True)
class MirrorIntegrity:
    authoritative_capture_count: int
    authoritative_journal_row_count: int
    authoritative_manifest_row_count: int
    journal_mirror_status: str
    manifest_mirror_status: str
    repair_needed: bool
    authoritative_evidence_intact: bool = True

    def as_payload(self) -> dict[str, object]:
        return {
            "authoritative_capture_count": self.authoritative_capture_count,
            "authoritative_journal_row_count": self.authoritative_journal_row_count,
            "authoritative_manifest_row_count": self.authoritative_manifest_row_count,
            "journal_mirror_status": self.journal_mirror_status,
            "manifest_mirror_status": self.manifest_mirror_status,
            "repair_needed": self.repair_needed,
            "authoritative_evidence_intact": self.authoritative_evidence_intact,
        }


def _read_jsonl_best_effort(path: Path) -> tuple[str, list[dict[str, Any]]]:
    if not path.exists():
        return "missing", []
    rows: list[dict[str, Any]] = []
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            value = json.loads(raw)
            if not isinstance(value, dict):
                return "corrupt", []
            rows.append(value)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return "corrupt", []
    return "readable", rows


def _journal_signature(rows: list[dict[str, Any]]) -> list[tuple[str, str, str]]:
    return sorted(
        (
            str(row.get("as_of_trade_date") or ""),
            str(row.get("candidate_key") or ""),
            str(row.get("capture_transaction_id") or ""),
        )
        for row in rows
    )


def _manifest_signature(
    rows: list[dict[str, Any]],
) -> list[tuple[str, int, int, str, str, str]]:
    return sorted(
        (
            str(row.get("as_of_trade_date") or ""),
            int(row.get("candidate_count") or 0),
            int(row.get("cohort_followup_count") or 0),
            str(row.get("capture_transaction_id") or ""),
            str(row.get("methodology_contract_version") or ""),
            str(row.get("methodology_fingerprint") or ""),
        )
        for row in rows
    )


def authoritative_mirror_payloads(
    transaction_root: str | Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    committed = read_committed_captures(transaction_root)
    if not committed:
        return [], [], 0
    baseline_present = frozen_legacy_baseline_present(transaction_root)
    baseline = read_frozen_legacy_baseline(transaction_root)
    if not baseline_present:
        raise RuntimeError(
            "committed transactions exist but frozen legacy baseline marker is missing"
        )
    journal_rows, manifest_rows = committed_capture_view(
        legacy_journal_rows=baseline,
        capture_rows=committed,
    )
    return journal_rows, manifest_rows, len(committed)


def inspect_compatibility_mirrors(
    *,
    transaction_root: str | Path,
    journal_path: str | Path,
    manifest_path: str | Path,
) -> MirrorIntegrity:
    authoritative_journal, authoritative_manifest, capture_count = (
        authoritative_mirror_payloads(transaction_root)
    )
    if capture_count == 0:
        return MirrorIntegrity(
            authoritative_capture_count=0,
            authoritative_journal_row_count=0,
            authoritative_manifest_row_count=0,
            journal_mirror_status="transaction_store_not_active",
            manifest_mirror_status="transaction_store_not_active",
            repair_needed=False,
        )

    journal_state, journal_rows = _read_jsonl_best_effort(Path(journal_path))
    manifest_state, manifest_rows = _read_jsonl_best_effort(Path(manifest_path))

    if journal_state == "readable":
        journal_state = (
            "current"
            if _journal_signature(journal_rows) == _journal_signature(authoritative_journal)
            else "drift"
        )
    if manifest_state == "readable":
        authoritative_tx_manifest = [
            row
            for row in authoritative_manifest
            if row.get("capture_transaction_id")
        ]
        mirror_tx_manifest = [
            row
            for row in manifest_rows
            if row.get("capture_transaction_id")
        ]
        manifest_state = (
            "current"
            if _manifest_signature(mirror_tx_manifest)
            == _manifest_signature(authoritative_tx_manifest)
            else "drift"
        )

    repair_needed = journal_state != "current" or manifest_state != "current"
    return MirrorIntegrity(
        authoritative_capture_count=capture_count,
        authoritative_journal_row_count=len(authoritative_journal),
        authoritative_manifest_row_count=len(authoritative_manifest),
        journal_mirror_status=journal_state,
        manifest_mirror_status=manifest_state,
        repair_needed=repair_needed,
    )


def _atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.repair.tmp")
    with tmp.open("wb") as handle:
        for row in rows:
            encoded = (
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                + "\n"
            ).encode("utf-8")
            handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp, path)


def repair_compatibility_mirrors(
    *,
    transaction_root: str | Path,
    journal_path: str | Path,
    manifest_path: str | Path,
) -> dict[str, Any]:
    journal_rows, manifest_rows, capture_count = authoritative_mirror_payloads(
        transaction_root
    )
    if capture_count == 0:
        return {
            "status": "not_applicable",
            "reason": "transaction_store_not_active",
            "authoritative_evidence_modified": False,
        }
    _atomic_write_jsonl(Path(journal_path), journal_rows)
    _atomic_write_jsonl(Path(manifest_path), manifest_rows)
    after = inspect_compatibility_mirrors(
        transaction_root=transaction_root,
        journal_path=journal_path,
        manifest_path=manifest_path,
    )
    if after.repair_needed:
        raise RuntimeError("compatibility mirror repair did not converge")
    return {
        "status": "repaired",
        "journal_rows": len(journal_rows),
        "manifest_rows": len(manifest_rows),
        "authoritative_evidence_modified": False,
        "integrity": after.as_payload(),
    }
