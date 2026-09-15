from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from .catalog import DataCatalog
from .universe import SUPPORTED_INITIAL_DAILY_PREFIXES
from .validation import DataValidationError, normalize_daily


@dataclass(slots=True)
class HealthIssue:
    instrument_id: str
    severity: str
    message: str


@dataclass(slots=True)
class HealthReport:
    checked: int
    uninitialized: int
    issues: list[HealthIssue]

    @property
    def errors(self) -> list[HealthIssue]:
        return [issue for issue in self.issues if issue.severity == "ERROR"]

    @property
    def warnings(self) -> list[HealthIssue]:
        return [issue for issue in self.issues if issue.severity == "WARN"]

    @property
    def passed(self) -> bool:
        return not self.errors


def audit_local_daily(catalog: DataCatalog) -> HealthReport:
    listed_ids = catalog.list_security_ids(listed_only=True)
    supported = [
        instrument_id
        for instrument_id in listed_ids
        if instrument_id.startswith(SUPPORTED_INITIAL_DAILY_PREFIXES)
    ]

    checked = 0
    uninitialized = 0
    issues: list[HealthIssue] = []

    for instrument_id in supported:
        metadata = catalog.get_daily(instrument_id)
        if metadata is None:
            uninitialized += 1
            continue

        checked += 1
        path = Path(str(metadata["parquet_path"]))
        if not path.exists():
            issues.append(HealthIssue(instrument_id, "ERROR", f"missing parquet: {path}"))
            continue

        try:
            frame = pd.read_parquet(path)
        except Exception as exc:
            issues.append(HealthIssue(instrument_id, "ERROR", f"cannot read parquet: {type(exc).__name__}: {exc}"))
            continue

        if frame.empty:
            issues.append(HealthIssue(instrument_id, "ERROR", "dataset is empty"))
            continue

        if "instrument_id" not in frame.columns:
            issues.append(HealthIssue(instrument_id, "ERROR", "instrument_id column missing"))
            continue

        actual_ids = set(frame["instrument_id"].astype(str).unique().tolist())
        if actual_ids != {instrument_id}:
            issues.append(
                HealthIssue(
                    instrument_id,
                    "ERROR",
                    f"instrument mismatch in parquet: {sorted(actual_ids)}",
                )
            )

        if "trade_date" in frame.columns:
            duplicate_count = int(frame.duplicated(subset=["instrument_id", "trade_date"]).sum())
            if duplicate_count:
                issues.append(
                    HealthIssue(instrument_id, "ERROR", f"duplicate trade dates: {duplicate_count}")
                )

        try:
            normalized = normalize_daily(frame)
        except (DataValidationError, ValueError, TypeError) as exc:
            issues.append(HealthIssue(instrument_id, "ERROR", f"validation failed: {exc}"))
            continue

        expected_rows = int(metadata["row_count"])
        actual_rows = len(normalized)
        if actual_rows != expected_rows:
            issues.append(
                HealthIssue(
                    instrument_id,
                    "ERROR",
                    f"row_count mismatch: catalog={expected_rows}, parquet={actual_rows}",
                )
            )

        first_date = pd.Timestamp(normalized["trade_date"].min()).date()
        last_date = pd.Timestamp(normalized["trade_date"].max()).date()
        if metadata["first_trade_date"] is not None and first_date != metadata["first_trade_date"]:
            issues.append(
                HealthIssue(
                    instrument_id,
                    "ERROR",
                    f"first date mismatch: catalog={metadata['first_trade_date']}, parquet={first_date}",
                )
            )
        if metadata["last_trade_date"] is not None and last_date != metadata["last_trade_date"]:
            issues.append(
                HealthIssue(
                    instrument_id,
                    "ERROR",
                    f"last date mismatch: catalog={metadata['last_trade_date']}, parquet={last_date}",
                )
            )

    return HealthReport(checked=checked, uninitialized=uninitialized, issues=issues)
