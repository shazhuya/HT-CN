from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from typing import Any


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
