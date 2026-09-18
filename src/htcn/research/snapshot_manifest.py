from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class CaptureTimeline:
    dates: tuple[str, ...]
    source: str
    legacy_pre_manifest_dates: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class SnapshotManifestEntry:
    code_head: str
    as_of_trade_date: str
    captured_at_utc: str
    instrument_count: int
    successful_instruments: int
    failed_instruments: int
    candidate_count: int
    worktree_clean: bool
    status: str
    capture_transaction_id: str | None = None
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def read_snapshot_manifest(path: str | Path) -> list[dict[str, Any]]:
    target = Path(path)
    if not target.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line_number, raw in enumerate(target.read_text(encoding="utf-8").splitlines(), start=1):
        if not raw.strip():
            continue
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid snapshot manifest JSONL at line {line_number}") from exc
        if not isinstance(value, dict):
            raise ValueError(f"invalid snapshot manifest row at line {line_number}")
        rows.append(value)
    return rows


def resolve_capture_timeline(
    journal_rows: list[dict[str, Any]],
    manifest_rows: list[dict[str, Any]] | None = None,
) -> CaptureTimeline:
    journal_dates = sorted({
        str(row.get("as_of_trade_date"))
        for row in journal_rows
        if row.get("as_of_trade_date")
    })
    journal_heads_by_date: dict[str, set[str]] = {}
    journal_count_by_date: dict[str, int] = {}
    for row in journal_rows:
        as_of = str(row.get("as_of_trade_date") or "")
        if not as_of:
            raise ValueError("journal row missing as_of_trade_date")
        journal_heads_by_date.setdefault(as_of, set()).add(
            str(row.get("code_head") or "")
        )
        journal_count_by_date[as_of] = journal_count_by_date.get(as_of, 0) + 1
    for as_of, heads in journal_heads_by_date.items():
        if "" in heads or len(heads) != 1:
            raise ValueError(
                f"journal date {as_of} does not have exactly one code head: {sorted(heads)}"
            )

    manifest = list(manifest_rows or [])
    if not manifest:
        return CaptureTimeline(
            dates=tuple(journal_dates),
            source="journal_fallback",
            legacy_pre_manifest_dates=tuple(journal_dates),
        )

    manifest_by_date: dict[str, dict[str, Any]] = {}
    for row in manifest:
        as_of = str(row.get("as_of_trade_date") or "")
        if not as_of:
            raise ValueError("snapshot manifest row missing as_of_trade_date")
        if as_of in manifest_by_date:
            raise ValueError(f"duplicate snapshot manifest date: {as_of}")
        if row.get("status") != "pass":
            raise ValueError(f"snapshot manifest {as_of} status is not pass")
        instrument_count = int(row.get("instrument_count") or 0)
        successful = int(row.get("successful_instruments") or 0)
        failed = int(row.get("failed_instruments") or 0)
        if instrument_count <= 0 or successful != instrument_count or failed != 0:
            raise ValueError(f"snapshot manifest {as_of} instrument coverage is incomplete")
        if row.get("worktree_clean") is not True:
            raise ValueError(f"snapshot manifest {as_of} was captured from dirty worktree")
        if row.get("alpha_inference_allowed") is not False:
            raise ValueError(f"snapshot manifest {as_of} unexpectedly permits alpha inference")
        if row.get("is_trade_instruction") is not False:
            raise ValueError(f"snapshot manifest {as_of} unexpectedly permits trade instruction")
        manifest_by_date[as_of] = row

    manifest_dates = sorted(manifest_by_date)
    first_manifest = manifest_dates[0]
    legacy = tuple(value for value in journal_dates if value < first_manifest)
    for as_of in journal_dates:
        if as_of >= first_manifest and as_of not in manifest_by_date:
            raise ValueError(
                f"journal date {as_of} is missing required snapshot manifest after manifest activation"
            )
        if as_of in manifest_by_date:
            journal_head = next(iter(journal_heads_by_date[as_of]))
            manifest_head = str(manifest_by_date[as_of].get("code_head") or "")
            if journal_head != manifest_head:
                raise ValueError(
                    f"snapshot manifest / journal code-head mismatch on {as_of}: "
                    f"{manifest_head} != {journal_head}"
                )
            manifest_candidates = int(
                manifest_by_date[as_of].get("candidate_count") or 0
            )
            journal_candidates = journal_count_by_date.get(as_of, 0)
            if manifest_candidates != journal_candidates:
                raise ValueError(
                    f"snapshot manifest / journal candidate-count mismatch on {as_of}: "
                    f"{manifest_candidates} != {journal_candidates}"
                )

    for as_of in manifest_dates:
        if as_of not in journal_count_by_date:
            manifest_candidates = int(
                manifest_by_date[as_of].get("candidate_count") or 0
            )
            if manifest_candidates != 0:
                raise ValueError(
                    f"snapshot manifest {as_of} reports {manifest_candidates} candidates "
                    "but journal has no rows"
                )

    dates = tuple(sorted(set(journal_dates) | set(manifest_dates)))
    return CaptureTimeline(
        dates=dates,
        source=("manifest" if not legacy else "manifest_plus_legacy_journal"),
        legacy_pre_manifest_dates=legacy,
    )


def append_snapshot_manifest(
    path: str | Path,
    entry: SnapshotManifestEntry,
) -> dict[str, int | str]:
    target = Path(path)
    existing = read_snapshot_manifest(target)
    dates = [str(row.get("as_of_trade_date")) for row in existing if row.get("as_of_trade_date")]
    if dates and entry.as_of_trade_date < max(dates):
        raise ValueError(
            f"snapshot manifest forbids backfill: {entry.as_of_trade_date} < {max(dates)}"
        )

    same_date = [
        row
        for row in existing
        if str(row.get("as_of_trade_date")) == entry.as_of_trade_date
    ]
    if same_date:
        heads = {str(row.get("code_head")) for row in same_date}
        if heads != {entry.code_head}:
            raise ValueError(
                f"snapshot manifest forbids mixed code heads on {entry.as_of_trade_date}: "
                f"existing={sorted(heads)} incoming={entry.code_head}"
            )
        incoming = entry.as_payload()
        for row in same_date:
            comparable = {
                key: row.get(key)
                for key in incoming
                if key != "captured_at_utc"
            }
            incoming_comparable = {
                key: value
                for key, value in incoming.items()
                if key != "captured_at_utc"
            }
            if comparable != incoming_comparable:
                raise ValueError(
                    f"snapshot manifest same-day rerun changed capture facts on {entry.as_of_trade_date}"
                )
        return {
            "existing": len(existing),
            "appended": 0,
            "as_of_trade_date": entry.as_of_trade_date,
        }

    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(entry.as_payload(), ensure_ascii=False, sort_keys=True))
        handle.write("\n")
    return {
        "existing": len(existing),
        "appended": 1,
        "as_of_trade_date": entry.as_of_trade_date,
    }
