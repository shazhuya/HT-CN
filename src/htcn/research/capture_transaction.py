from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import json
import os
from typing import Any, Iterable

from .cohort_followup import enrolled_outcome_cohort


CAPTURE_TRANSACTION_SCHEMA_VERSION = 3
LEGACY_BASELINE_SCHEMA_VERSION = 1
SUPPORTED_CAPTURE_TRANSACTION_SCHEMA_VERSIONS = (1, 2, 3)


@dataclass(frozen=True, slots=True)
class CommittedCapture:
    transaction_id: str
    code_head: str
    as_of_trade_date: str
    captured_at_utc: str
    instrument_count: int
    successful_instruments: int
    failed_instruments: int
    candidate_count: int
    cohort_followup_count: int
    worktree_clean: bool
    methodology_contract_version: int
    methodology_fingerprint: str
    journal_rows: tuple[dict[str, Any], ...]
    cohort_followup_rows: tuple[dict[str, Any], ...]
    status: str = "committed"
    schema_version: int = CAPTURE_TRANSACTION_SCHEMA_VERSION
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["journal_rows"] = [dict(row) for row in self.journal_rows]
        payload["cohort_followup_rows"] = [
            dict(row) for row in self.cohort_followup_rows
        ]
        return payload


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _transaction_identity_payload(
    *,
    code_head: str,
    as_of_trade_date: str,
    instrument_count: int,
    successful_instruments: int,
    failed_instruments: int,
    journal_rows: Iterable[dict[str, Any]],
    cohort_followup_rows: Iterable[dict[str, Any]] = (),
    methodology_contract_version: int | None = None,
    methodology_fingerprint: str | None = None,
    schema_version: int = CAPTURE_TRANSACTION_SCHEMA_VERSION,
) -> dict[str, Any]:
    rows = [dict(row) for row in journal_rows]
    rows.sort(key=lambda row: str(row.get("candidate_key") or ""))
    normalized_rows: list[dict[str, Any]] = []
    for row in rows:
        clean = dict(row)
        clean.pop("capture_transaction_id", None)
        clean.pop("enrollment_state", None)
        clean.pop("first_observed_trade_date", None)
        clean.pop("prospective_outcome_eligible", None)
        clean.pop("outcome_enrollment_trade_date", None)
        clean.pop("outcome_eligibility_reason", None)
        normalized_rows.append(clean)
    followups = [dict(row) for row in cohort_followup_rows]
    followups.sort(key=lambda row: str(row.get("candidate_key") or ""))
    normalized_followups: list[dict[str, Any]] = []
    for row in followups:
        clean = dict(row)
        clean.pop("capture_transaction_id", None)
        normalized_followups.append(clean)

    payload: dict[str, Any] = {
        "schema_version": int(schema_version),
        "code_head": code_head,
        "as_of_trade_date": as_of_trade_date,
        "instrument_count": int(instrument_count),
        "successful_instruments": int(successful_instruments),
        "failed_instruments": int(failed_instruments),
        "candidate_count": len(normalized_rows),
        "journal_rows": normalized_rows,
    }
    if int(schema_version) >= 3:
        payload["cohort_followup_count"] = len(normalized_followups)
        payload["cohort_followup_rows"] = normalized_followups
    if int(schema_version) >= 2:
        _validate_methodology_identity(
            methodology_contract_version=methodology_contract_version,
            methodology_fingerprint=methodology_fingerprint,
            source="capture transaction identity",
        )
        payload["methodology_contract_version"] = int(
            methodology_contract_version
        )
        payload["methodology_fingerprint"] = str(methodology_fingerprint)
    return payload


def capture_transaction_id(
    *,
    code_head: str,
    as_of_trade_date: str,
    instrument_count: int,
    successful_instruments: int,
    failed_instruments: int,
    journal_rows: Iterable[dict[str, Any]],
    cohort_followup_rows: Iterable[dict[str, Any]] = (),
    methodology_contract_version: int | None = None,
    methodology_fingerprint: str | None = None,
    schema_version: int = CAPTURE_TRANSACTION_SCHEMA_VERSION,
) -> str:
    identity = _transaction_identity_payload(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        instrument_count=instrument_count,
        successful_instruments=successful_instruments,
        failed_instruments=failed_instruments,
        journal_rows=journal_rows,
        cohort_followup_rows=cohort_followup_rows,
        methodology_contract_version=methodology_contract_version,
        methodology_fingerprint=methodology_fingerprint,
        schema_version=schema_version,
    )
    return sha256(_canonical_json(identity).encode("utf-8")).hexdigest()[:24]


def _validate_methodology_identity(
    *,
    methodology_contract_version: int | None,
    methodology_fingerprint: str | None,
    source: str,
) -> None:
    if methodology_contract_version is None or int(methodology_contract_version) <= 0:
        raise ValueError(f"missing methodology contract version: {source}")
    fingerprint = str(methodology_fingerprint or "")
    if len(fingerprint) != 64:
        raise ValueError(f"invalid methodology fingerprint length: {source}")
    try:
        int(fingerprint, 16)
    except ValueError as exc:
        raise ValueError(f"invalid methodology fingerprint encoding: {source}") from exc


def _validate_market_observation_row(
    row: dict[str, Any],
) -> None:
    status = str(row.get("market_observation_status") or "traded")
    as_of = str(row.get("as_of_trade_date") or "")
    underlying_raw = row.get("underlying_last_trade_date")
    underlying = None if underlying_raw is None else str(underlying_raw)

    if status == "traded":
        if underlying is not None and underlying != as_of:
            raise ValueError(
                "traded observation underlying_last_trade_date must equal as_of"
            )
        return

    if status != "confirmed_full_day_suspended":
        raise ValueError(
            f"unsupported market_observation_status: {status}"
        )
    if underlying is None or not as_of or underlying >= as_of:
        raise ValueError(
            "suspended observation requires underlying_last_trade_date before as_of"
        )
    if str(row.get("execution_context_gate") or "") != "blocked_suspended":
        raise ValueError(
            "suspended observation requires execution_context_gate=blocked_suspended"
        )
    if not str(row.get("daily_event_source") or ""):
        raise ValueError(
            "suspended observation requires positive daily_event_source evidence"
        )
    raw_fields = (
        "as_of_open",
        "as_of_high",
        "as_of_low",
        "as_of_close",
        "as_of_volume",
    )
    if any(row.get(field) is not None for field in raw_fields):
        raise ValueError(
            "suspended observation must not contain synthetic as-of OHLC/volume"
        )


def _validate_rows(
    *,
    code_head: str,
    as_of_trade_date: str,
    journal_rows: list[dict[str, Any]],
) -> None:
    keys: list[str] = []
    for row in journal_rows:
        if str(row.get("code_head") or "") != code_head:
            raise ValueError("capture transaction journal row code_head mismatch")
        if str(row.get("as_of_trade_date") or "") != as_of_trade_date:
            raise ValueError("capture transaction journal row as-of mismatch")
        key = str(row.get("candidate_key") or "")
        if not key:
            raise ValueError("capture transaction journal row missing candidate_key")
        keys.append(key)
        if row.get("alpha_inference_allowed") is not False:
            raise ValueError("capture transaction row unexpectedly permits alpha inference")
        if row.get("is_trade_instruction") is not False:
            raise ValueError("capture transaction row unexpectedly permits trade instruction")
        _validate_market_observation_row(row)
    if len(keys) != len(set(keys)):
        raise ValueError("capture transaction contains duplicate candidate_key")



def _validate_followup_rows(
    *,
    code_head: str,
    as_of_trade_date: str,
    journal_rows: list[dict[str, Any]],
    followup_rows: list[dict[str, Any]],
) -> None:
    journal_keys = {
        str(row.get("candidate_key") or "")
        for row in journal_rows
    }
    keys: list[str] = []
    for row in followup_rows:
        if str(row.get("code_head") or "") != code_head:
            raise ValueError("capture follow-up row code_head mismatch")
        if str(row.get("as_of_trade_date") or "") != as_of_trade_date:
            raise ValueError("capture follow-up row as-of mismatch")
        key = str(row.get("candidate_key") or "")
        instrument_id = str(row.get("instrument_id") or "")
        enrollment = str(row.get("outcome_enrollment_trade_date") or "")
        if not key or not instrument_id or not enrollment:
            raise ValueError(
                "capture follow-up row missing candidate/instrument/enrollment"
            )
        if enrollment >= as_of_trade_date:
            raise ValueError(
                "capture follow-up requires prior outcome enrollment date"
            )
        if str(row.get("scanner_presence") or "") != "absent":
            raise ValueError("capture follow-up row must be scanner absent")
        if key in journal_keys:
            raise ValueError(
                "capture candidate cannot be scanner-present and follow-up-absent "
                "in the same transaction"
            )
        if row.get("alpha_inference_allowed") is not False:
            raise ValueError(
                "capture follow-up unexpectedly permits alpha inference"
            )
        if row.get("is_trade_instruction") is not False:
            raise ValueError(
                "capture follow-up unexpectedly permits trade instruction"
            )
        status = str(row.get("market_observation_status") or "traded")
        if status == "traded":
            if str(row.get("execution_context_gate") or "") != "followup_observation_only":
                raise ValueError(
                    "traded follow-up requires execution_context_gate="
                    "followup_observation_only"
                )
            for field in (
                "as_of_open",
                "as_of_high",
                "as_of_low",
                "as_of_close",
                "as_of_volume",
            ):
                if row.get(field) is None:
                    raise ValueError(
                        f"traded follow-up missing market fact: {field}"
                    )
        _validate_market_observation_row(row)
        keys.append(key)
    if len(keys) != len(set(keys)):
        raise ValueError("capture transaction contains duplicate follow-up candidate_key")


def _validate_committed_payload(
    payload: dict[str, Any],
    *,
    source: str,
) -> tuple[str, str, list[dict[str, Any]]]:
    if payload.get("status") != "committed":
        raise ValueError(f"capture transaction is not committed: {source}")
    schema_version = int(payload.get("schema_version") or 0)
    if schema_version not in SUPPORTED_CAPTURE_TRANSACTION_SCHEMA_VERSIONS:
        raise ValueError(f"unsupported capture transaction schema: {source}")
    methodology_contract_version = payload.get("methodology_contract_version")
    methodology_fingerprint = payload.get("methodology_fingerprint")
    if schema_version >= 2:
        _validate_methodology_identity(
            methodology_contract_version=(
                None
                if methodology_contract_version is None
                else int(methodology_contract_version)
            ),
            methodology_fingerprint=(
                None
                if methodology_fingerprint is None
                else str(methodology_fingerprint)
            ),
            source=source,
        )
    if payload.get("worktree_clean") is not True:
        raise ValueError(f"capture transaction was not from clean worktree: {source}")
    if payload.get("alpha_inference_allowed") is not False:
        raise ValueError(f"capture transaction unexpectedly permits alpha inference: {source}")
    if payload.get("is_trade_instruction") is not False:
        raise ValueError(f"capture transaction unexpectedly permits trade instruction: {source}")
    if not str(payload.get("captured_at_utc") or ""):
        raise ValueError(f"capture transaction missing captured_at_utc: {source}")
    code_head = str(payload.get("code_head") or "")
    as_of = str(payload.get("as_of_trade_date") or "")
    if not code_head or not as_of:
        raise ValueError(f"capture transaction missing code_head/as_of: {source}")
    instrument_count = int(payload.get("instrument_count") or 0)
    successful = int(payload.get("successful_instruments") or 0)
    failed = int(payload.get("failed_instruments") or 0)
    if instrument_count <= 0 or successful != instrument_count or failed != 0:
        raise ValueError(f"capture transaction instrument coverage is incomplete: {source}")
    rows = [dict(row) for row in payload.get("journal_rows") or []]
    followups = [
        dict(row) for row in payload.get("cohort_followup_rows") or []
    ]
    if schema_version < 3 and followups:
        raise ValueError(
            f"pre-v3 capture transaction cannot contain follow-up rows: {source}"
        )
    _validate_rows(
        code_head=code_head,
        as_of_trade_date=as_of,
        journal_rows=rows,
    )
    if int(payload.get("candidate_count") or 0) != len(rows):
        raise ValueError(f"capture transaction candidate_count mismatch: {source}")
    if schema_version >= 3:
        _validate_followup_rows(
            code_head=code_head,
            as_of_trade_date=as_of,
            journal_rows=rows,
            followup_rows=followups,
        )
        if int(payload.get("cohort_followup_count") or 0) != len(followups):
            raise ValueError(
                f"capture transaction cohort_followup_count mismatch: {source}"
            )
    txid = str(payload.get("transaction_id") or "")
    expected = capture_transaction_id(
        code_head=code_head,
        as_of_trade_date=as_of,
        instrument_count=instrument_count,
        successful_instruments=successful,
        failed_instruments=failed,
        journal_rows=rows,
        cohort_followup_rows=followups,
        methodology_contract_version=(
            None
            if methodology_contract_version is None
            else int(methodology_contract_version)
        ),
        methodology_fingerprint=(
            None
            if methodology_fingerprint is None
            else str(methodology_fingerprint)
        ),
        schema_version=schema_version,
    )
    if txid != expected:
        raise ValueError(f"capture transaction id mismatch: {source}")
    for row in [*rows, *followups]:
        if str(row.get("capture_transaction_id") or "") != txid:
            raise ValueError(
                f"capture transaction row transaction-id mismatch: {source}"
            )
    return as_of, txid, rows


def _validate_legacy_rows(
    rows: list[dict[str, Any]],
    *,
    baseline_through_trade_date: str | None,
) -> None:
    keys_by_date: dict[str, list[str]] = {}
    heads_by_date: dict[str, set[str]] = {}
    row_dates: list[str] = []
    for row in rows:
        as_of = str(row.get("as_of_trade_date") or "")
        code_head = str(row.get("code_head") or "")
        key = str(row.get("candidate_key") or "")
        if not as_of or not code_head or not key:
            raise ValueError("legacy baseline row missing date/head/candidate_key")
        if row.get("alpha_inference_allowed") is not False:
            raise ValueError("legacy baseline row unexpectedly permits alpha inference")
        if row.get("is_trade_instruction") is not False:
            raise ValueError("legacy baseline row unexpectedly permits trade instruction")
        row_dates.append(as_of)
        keys_by_date.setdefault(as_of, []).append(key)
        heads_by_date.setdefault(as_of, set()).add(code_head)
    for as_of, keys in keys_by_date.items():
        if len(keys) != len(set(keys)):
            raise ValueError(f"legacy baseline duplicate candidate_key on {as_of}")
        heads = heads_by_date[as_of]
        if len(heads) != 1:
            raise ValueError(f"legacy baseline mixed code heads on {as_of}")
    if row_dates and baseline_through_trade_date is None:
        raise ValueError("legacy baseline with rows requires cutoff date")
    if row_dates and max(row_dates) > str(baseline_through_trade_date):
        raise ValueError(
            "legacy baseline contains row after baseline_through_trade_date"
        )

def build_committed_capture(
    *,
    code_head: str,
    as_of_trade_date: str,
    captured_at_utc: str,
    instrument_count: int,
    successful_instruments: int,
    failed_instruments: int,
    worktree_clean: bool,
    methodology_contract_version: int,
    methodology_fingerprint: str,
    journal_rows: Iterable[dict[str, Any]],
    cohort_followup_rows: Iterable[dict[str, Any]] = (),
) -> CommittedCapture:
    rows = [dict(row) for row in journal_rows]
    rows.sort(key=lambda row: str(row.get("candidate_key") or ""))
    followups = [dict(row) for row in cohort_followup_rows]
    followups.sort(key=lambda row: str(row.get("candidate_key") or ""))
    if not code_head:
        raise ValueError("capture transaction requires code_head")
    if not as_of_trade_date:
        raise ValueError("capture transaction requires as_of_trade_date")
    if instrument_count <= 0:
        raise ValueError("capture transaction requires positive instrument_count")
    if successful_instruments != instrument_count or failed_instruments != 0:
        raise ValueError("capture transaction requires complete instrument coverage")
    if worktree_clean is not True:
        raise ValueError("capture transaction requires clean worktree")
    _validate_methodology_identity(
        methodology_contract_version=methodology_contract_version,
        methodology_fingerprint=methodology_fingerprint,
        source="build_committed_capture",
    )
    _validate_rows(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        journal_rows=rows,
    )
    _validate_followup_rows(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        journal_rows=rows,
        followup_rows=followups,
    )
    txid = capture_transaction_id(
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        instrument_count=instrument_count,
        successful_instruments=successful_instruments,
        failed_instruments=failed_instruments,
        journal_rows=rows,
        cohort_followup_rows=followups,
        methodology_contract_version=methodology_contract_version,
        methodology_fingerprint=methodology_fingerprint,
    )
    stamped = tuple({**row, "capture_transaction_id": txid} for row in rows)
    stamped_followups = tuple(
        {**row, "capture_transaction_id": txid}
        for row in followups
    )
    return CommittedCapture(
        transaction_id=txid,
        code_head=code_head,
        as_of_trade_date=as_of_trade_date,
        captured_at_utc=captured_at_utc,
        instrument_count=instrument_count,
        successful_instruments=successful_instruments,
        failed_instruments=failed_instruments,
        candidate_count=len(stamped),
        cohort_followup_count=len(stamped_followups),
        worktree_clean=worktree_clean,
        methodology_contract_version=methodology_contract_version,
        methodology_fingerprint=methodology_fingerprint,
        journal_rows=stamped,
        cohort_followup_rows=stamped_followups,
    )


def _capture_filename(capture: CommittedCapture) -> str:
    return f"{capture.as_of_trade_date}__{capture.transaction_id}.json"



def _validate_followup_chain(
    root: str | Path,
    captures: Iterable[dict[str, Any]],
) -> None:
    ordered = sorted(
        [dict(item) for item in captures],
        key=lambda item: str(item.get("as_of_trade_date") or ""),
    )
    if not ordered:
        return

    if not _legacy_baseline_path(root).exists():
        if any(item.get("cohort_followup_rows") for item in ordered):
            raise ValueError(
                "cohort follow-up evidence requires frozen legacy baseline"
            )
        return

    baseline_rows = read_frozen_legacy_baseline(root)
    baseline_trade_date = frozen_legacy_baseline_through_date(root)
    prior_journal = [dict(row) for row in baseline_rows]

    for capture in ordered:
        as_of = str(capture.get("as_of_trade_date") or "")
        prior_cohort = enrolled_outcome_cohort(
            prior_journal,
            baseline_trade_date=baseline_trade_date,
        )
        present_keys = {
            str(row.get("candidate_key") or "")
            for row in capture.get("journal_rows") or []
        }
        followup_rows = [
            dict(row) for row in capture.get("cohort_followup_rows") or []
        ]
        followup_keys = {
            str(row.get("candidate_key") or "")
            for row in followup_rows
        }
        expected_followup_keys = set(prior_cohort) - present_keys
        if int(capture.get("schema_version") or 0) >= 3:
            if followup_keys != expected_followup_keys:
                missing = sorted(expected_followup_keys - followup_keys)
                extra = sorted(followup_keys - expected_followup_keys)
                raise ValueError(
                    "cohort follow-up coverage mismatch on "
                    f"{as_of}: missing={missing} extra={extra}"
                )

        for followup in followup_rows:
            key = str(followup.get("candidate_key") or "")
            expected = prior_cohort.get(key)
            if expected is None:
                raise ValueError(
                    f"cohort follow-up candidate was not previously outcome-enrolled: {key}"
                )
            if key in present_keys:
                raise ValueError(
                    f"cohort follow-up candidate is scanner-present on {as_of}: {key}"
                )
            if (
                str(followup.get("instrument_id") or "")
                != expected["instrument_id"]
            ):
                raise ValueError(
                    f"cohort follow-up instrument identity drift: {key}"
                )
            if (
                str(followup.get("outcome_enrollment_trade_date") or "")
                != expected["outcome_enrollment_trade_date"]
            ):
                raise ValueError(
                    f"cohort follow-up enrollment date drift: {key}"
                )

        prior_journal.extend(
            dict(row) for row in capture.get("journal_rows") or []
        )


def commit_capture_transaction(
    root: str | Path,
    capture: CommittedCapture,
) -> dict[str, Any]:
    target_root = Path(root)
    target_root.mkdir(parents=True, exist_ok=True)
    final_path = target_root / _capture_filename(capture)

    existing_payloads = read_committed_captures(target_root)
    for existing in existing_payloads:
        existing_version = existing.get("methodology_contract_version")
        existing_fingerprint = str(existing.get("methodology_fingerprint") or "")
        if existing_version is None or not existing_fingerprint:
            raise ValueError(
                "existing committed capture predates methodology fingerprint; "
                "explicit methodology migration is required"
            )
        if int(existing.get("schema_version") or 0) != capture.schema_version:
            raise ValueError(
                "capture transaction schema drift across active chain; "
                "start an explicit migration epoch instead of mixing schemas"
            )
        if (
            int(existing_version) != capture.methodology_contract_version
            or existing_fingerprint != capture.methodology_fingerprint
        ):
            raise ValueError(
                "methodology fingerprint drift across committed capture chain; "
                "start an explicitly versioned methodology epoch instead of mixing evidence"
            )

    _validate_followup_chain(
        target_root,
        [*existing_payloads, capture.as_payload()],
    )

    existing_paths = sorted(target_root.glob("????-??-??__*.json"))
    existing_dates = [path.name.split("__", 1)[0] for path in existing_paths]
    if existing_dates and capture.as_of_trade_date < max(existing_dates):
        raise ValueError(
            f"capture transaction forbids backfill: {capture.as_of_trade_date} < {max(existing_dates)}"
        )

    baseline_path = _legacy_baseline_path(target_root)
    if baseline_path.exists():
        baseline_through = frozen_legacy_baseline_through_date(target_root)
        if baseline_through and capture.as_of_trade_date <= baseline_through:
            raise ValueError(
                f"capture transaction must be after frozen legacy baseline: "
                f"{capture.as_of_trade_date} <= {baseline_through}"
            )

    same_date = [
        path
        for path in existing_paths
        if path.name.startswith(f"{capture.as_of_trade_date}__")
    ]
    for path in same_date:
        if path.name == final_path.name:
            existing = json.loads(path.read_text(encoding="utf-8"))
            existing_as_of, existing_txid, _ = _validate_committed_payload(
                existing,
                source=str(path),
            )
            if existing_as_of != capture.as_of_trade_date:
                raise ValueError(
                    f"committed capture as-of drift for {capture.as_of_trade_date}"
                )
            if existing_txid != capture.transaction_id:
                raise ValueError(
                    f"committed capture transaction-id drift for {capture.as_of_trade_date}"
                )
            return {
                "status": "already_committed",
                "transaction_id": capture.transaction_id,
                "path": str(final_path),
            }
        raise ValueError(
            f"capture date {capture.as_of_trade_date} already has another committed transaction: {path.name}"
        )

    tmp_path = target_root / f".{final_path.name}.tmp"
    encoded = (_canonical_json(capture.as_payload()) + "\n").encode("utf-8")
    with tmp_path.open("wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, final_path)
    return {
        "status": "committed",
        "transaction_id": capture.transaction_id,
        "path": str(final_path),
    }


def read_committed_captures(root: str | Path) -> list[dict[str, Any]]:
    target_root = Path(root)
    if not target_root.exists():
        return []
    captures: list[dict[str, Any]] = []
    dates: set[str] = set()
    for path in sorted(target_root.glob("????-??-??__*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        as_of, txid, _ = _validate_committed_payload(
            payload,
            source=str(path),
        )
        expected_name = f"{as_of}__{txid}.json"
        if path.name != expected_name:
            raise ValueError(
                f"capture transaction filename mismatch: {path.name} != {expected_name}"
            )
        if as_of in dates:
            raise ValueError(f"multiple committed capture transactions on {as_of}")
        dates.add(as_of)
        captures.append(payload)
    captures.sort(key=lambda item: str(item.get("as_of_trade_date")))
    methodology_keys = {
        (
            item.get("methodology_contract_version"),
            str(item.get("methodology_fingerprint") or ""),
        )
        for item in captures
    }
    if len(methodology_keys) > 1:
        raise ValueError(
            "committed capture chain contains mixed methodology fingerprints"
        )
    schema_versions = {
        int(item.get("schema_version") or 0)
        for item in captures
    }
    if len(schema_versions) > 1:
        raise ValueError(
            "committed capture chain contains mixed transaction schemas"
        )
    _validate_followup_chain(target_root, captures)
    return captures

def committed_capture_view(
    *,
    legacy_journal_rows: Iterable[dict[str, Any]],
    capture_rows: Iterable[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    legacy = [dict(row) for row in legacy_journal_rows]
    captures = [dict(row) for row in capture_rows]
    if not captures:
        return legacy, []
    first_capture_date = min(str(item["as_of_trade_date"]) for item in captures)
    legacy_only = [
        row
        for row in legacy
        if str(row.get("as_of_trade_date") or "") < first_capture_date
    ]
    journal_rows = list(legacy_only)
    manifest_rows: list[dict[str, Any]] = []
    for capture in sorted(captures, key=lambda item: str(item["as_of_trade_date"])):
        txid = str(capture["transaction_id"])
        for row in capture.get("journal_rows") or []:
            journal_rows.append({**dict(row), "capture_transaction_id": txid})
        manifest_rows.append({
            "capture_transaction_id": txid,
            "code_head": capture["code_head"],
            "as_of_trade_date": capture["as_of_trade_date"],
            "captured_at_utc": capture["captured_at_utc"],
            "instrument_count": capture["instrument_count"],
            "successful_instruments": capture["successful_instruments"],
            "failed_instruments": capture["failed_instruments"],
            "candidate_count": capture["candidate_count"],
            "cohort_followup_count": int(
                capture.get("cohort_followup_count") or 0
            ),
            "worktree_clean": capture["worktree_clean"],
            "methodology_contract_version": capture.get(
                "methodology_contract_version"
            ),
            "methodology_fingerprint": capture.get("methodology_fingerprint"),
            "status": "pass",
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
        })
    return journal_rows, manifest_rows


def committed_followup_view(
    capture_rows: Iterable[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for capture in sorted(
        [dict(item) for item in capture_rows],
        key=lambda item: str(item.get("as_of_trade_date") or ""),
    ):
        txid = str(capture.get("transaction_id") or "")
        for row in capture.get("cohort_followup_rows") or []:
            rows.append({**dict(row), "capture_transaction_id": txid})
    return rows


def _legacy_baseline_path(root: str | Path) -> Path:
    return Path(root) / "legacy_baseline.json"


def _legacy_baseline_id(rows: Iterable[dict[str, Any]]) -> str:
    materialized = [dict(row) for row in rows]
    materialized.sort(
        key=lambda row: (
            str(row.get("as_of_trade_date") or ""),
            str(row.get("candidate_key") or ""),
        )
    )
    return sha256(_canonical_json(materialized).encode("utf-8")).hexdigest()[:24]


def freeze_legacy_baseline(
    root: str | Path,
    rows: Iterable[dict[str, Any]],
    *,
    baseline_through_trade_date: str | None = None,
) -> dict[str, Any]:
    target_root = Path(root)
    target_root.mkdir(parents=True, exist_ok=True)
    materialized = [dict(row) for row in rows]
    materialized.sort(
        key=lambda row: (
            str(row.get("as_of_trade_date") or ""),
            str(row.get("candidate_key") or ""),
        )
    )
    inferred_dates = sorted({
        str(row.get("as_of_trade_date"))
        for row in materialized
        if row.get("as_of_trade_date")
    })
    baseline_through = (
        str(baseline_through_trade_date)
        if baseline_through_trade_date is not None
        else (inferred_dates[-1] if inferred_dates else None)
    )
    identity_payload = {
        "journal_rows": materialized,
        "baseline_through_trade_date": baseline_through,
    }
    baseline_id = sha256(
        _canonical_json(identity_payload).encode("utf-8")
    ).hexdigest()[:24]
    _validate_legacy_rows(
        materialized,
        baseline_through_trade_date=baseline_through,
    )
    payload = {
        "schema_version": LEGACY_BASELINE_SCHEMA_VERSION,
        "status": "frozen_legacy_baseline",
        "baseline_id": baseline_id,
        "baseline_through_trade_date": baseline_through,
        "row_count": len(materialized),
        "journal_rows": materialized,
        "alpha_inference_allowed": False,
        "is_trade_instruction": False,
    }
    final_path = _legacy_baseline_path(target_root)
    if final_path.exists():
        read_frozen_legacy_baseline(target_root)
        existing = json.loads(final_path.read_text(encoding="utf-8"))
        if str(existing.get("baseline_id") or "") != baseline_id:
            raise ValueError("legacy baseline is already frozen with different evidence")
        return {
            "status": "already_frozen",
            "baseline_id": baseline_id,
            "path": str(final_path),
        }
    tmp_path = target_root / ".legacy_baseline.json.tmp"
    encoded = (_canonical_json(payload) + "\n").encode("utf-8")
    with tmp_path.open("wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(tmp_path, final_path)
    return {
        "status": "frozen",
        "baseline_id": baseline_id,
        "path": str(final_path),
    }


def read_frozen_legacy_baseline(root: str | Path) -> list[dict[str, Any]]:
    path = _legacy_baseline_path(root)
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("status") != "frozen_legacy_baseline":
        raise ValueError("legacy baseline status is invalid")
    if int(payload.get("schema_version") or 0) != LEGACY_BASELINE_SCHEMA_VERSION:
        raise ValueError("legacy baseline schema is invalid")
    rows = [dict(row) for row in payload.get("journal_rows") or []]
    baseline_through = payload.get("baseline_through_trade_date")
    identity_payload = {
        "journal_rows": sorted(
            rows,
            key=lambda row: (
                str(row.get("as_of_trade_date") or ""),
                str(row.get("candidate_key") or ""),
            ),
        ),
        "baseline_through_trade_date": baseline_through,
    }
    expected = sha256(
        _canonical_json(identity_payload).encode("utf-8")
    ).hexdigest()[:24]
    if str(payload.get("baseline_id") or "") != expected:
        raise ValueError("legacy baseline identity mismatch")
    if int(payload.get("row_count") or 0) != len(rows):
        raise ValueError("legacy baseline row_count mismatch")
    if payload.get("alpha_inference_allowed") is not False:
        raise ValueError("legacy baseline unexpectedly permits alpha inference")
    if payload.get("is_trade_instruction") is not False:
        raise ValueError("legacy baseline unexpectedly permits trade instruction")
    _validate_legacy_rows(
        rows,
        baseline_through_trade_date=(
            None if baseline_through is None else str(baseline_through)
        ),
    )
    return rows



def frozen_legacy_baseline_through_date(root: str | Path) -> str | None:
    path = _legacy_baseline_path(root)
    if not path.exists():
        return None
    # Validate the immutable baseline identity before trusting its cutoff.
    read_frozen_legacy_baseline(root)
    payload = json.loads(path.read_text(encoding="utf-8"))
    value = payload.get("baseline_through_trade_date")
    return None if value is None else str(value)



def frozen_legacy_baseline_present(root: str | Path) -> bool:
    path = _legacy_baseline_path(root)
    if not path.exists():
        return False
    read_frozen_legacy_baseline(root)
    return True
