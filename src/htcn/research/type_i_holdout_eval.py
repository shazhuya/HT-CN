from __future__ import annotations

from collections.abc import Iterable
from math import sqrt
from typing import Any

from .time_split import assign_purged_split
from .type_i_confirmation import (
    DEFAULT_TYPE_I_LANDMARK_BAR,
    _bar_value,
    _boundaries,
    _terminal_events,
)

DEFAULT_REACTION_HORIZON = 20


def wilson_interval(successes: int, total: int, *, z: float) -> tuple[float, float]:
    if total <= 0:
        raise ValueError("total must be > 0")
    if successes < 0 or successes > total:
        raise ValueError("successes must be between 0 and total")
    p = successes / total
    z2 = z * z
    denominator = 1.0 + z2 / total
    center = (p + z2 / (2.0 * total)) / denominator
    radius = (
        z
        * sqrt((p * (1.0 - p) / total) + (z2 / (4.0 * total * total)))
        / denominator
    )
    return max(0.0, center - radius), min(1.0, center + radius)


def newcombe_difference_interval(
    exposure_successes: int,
    exposure_total: int,
    comparator_successes: int,
    comparator_total: int,
    *,
    z: float,
) -> tuple[float, float]:
    """Newcombe score interval (method 10) for p_exposure - p_comparator."""
    if exposure_total <= 0 or comparator_total <= 0:
        raise ValueError("both groups require at least one observation")
    p1 = exposure_successes / exposure_total
    p0 = comparator_successes / comparator_total
    l1, u1 = wilson_interval(exposure_successes, exposure_total, z=z)
    l0, u0 = wilson_interval(comparator_successes, comparator_total, z=z)
    difference = p1 - p0
    lower = difference - sqrt((p1 - l1) ** 2 + (u0 - p0) ** 2)
    upper = difference + sqrt((u1 - p1) ** 2 + (p0 - l0) ** 2)
    return max(-1.0, lower), min(1.0, upper)


def _t2_pending(row: dict[str, Any], *, landmark_bar: int) -> bool:
    t2 = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_t2")
    return t2 is None or t2 > landmark_bar


def _endpoint_hit(
    row: dict[str, Any],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> bool:
    t2 = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_t2")
    return bool(t2 is not None and landmark_bar < t2 <= reaction_horizon)


def _full_exit_bar(row: dict[str, Any]) -> int | None:
    return _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_full_prz_exit")


def _belongs(row: dict[str, Any], group: str) -> bool:
    exit_bar = _full_exit_bar(row)
    if group == "full_prz_exit_by_t5":
        return exit_bar is not None and 1 <= exit_bar <= 5
    if group == "no_full_exit_by_t5":
        return exit_bar is None or exit_bar > 5
    if group == "exit_by_t3":
        return exit_bar is not None and 1 <= exit_bar <= 3
    if group == "exit_on_t4_t5":
        return exit_bar is not None and 4 <= exit_bar <= 5
    raise ValueError(f"unsupported preregistered group: {group}")


def _group_summary(
    rows: Iterable[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    values = list(rows)
    hits = sum(
        _endpoint_hit(row, landmark_bar=landmark_bar, reaction_horizon=reaction_horizon)
        for row in values
    )
    return {
        "records": len(values),
        "endpoint_hits": int(hits),
        "endpoint_rate": None if not values else hits / len(values),
    }


def _descriptive_diagnostics(
    exposure: list[dict[str, Any]],
    comparator: list[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    dimensions = ("direction", "pattern_family", "source_scale", "instrument_id")
    out: dict[str, Any] = {}
    for dimension in dimensions:
        values = sorted(
            {str(row.get(dimension)) for row in exposure + comparator}
        )
        details: list[dict[str, Any]] = []
        for value in values:
            exp = [row for row in exposure if str(row.get(dimension)) == value]
            comp = [row for row in comparator if str(row.get(dimension)) == value]
            details.append(
                {
                    "value": value,
                    "exposure": _group_summary(
                        exp,
                        landmark_bar=landmark_bar,
                        reaction_horizon=reaction_horizon,
                    ),
                    "comparator": _group_summary(
                        comp,
                        landmark_bar=landmark_bar,
                        reaction_horizon=reaction_horizon,
                    ),
                }
            )
        out[dimension] = details
    return out


def evaluate_preregistered_type_i_holdout(
    records: Iterable[dict[str, Any]],
    terminal_bar_calibration: dict[str, Any],
    preregistration: dict[str, Any],
    authorization: dict[str, Any],
    *,
    reaction_horizon: int = DEFAULT_REACTION_HORIZON,
    landmark_bar: int = DEFAULT_TYPE_I_LANDMARK_BAR,
) -> dict[str, Any]:
    """Open the sealed M2.17 Holdout exactly as pre-registered.

    This function must only be called from the explicit one-time M2.22 authorization commit.
    It performs exactly one primary contrast and does not search alternate thresholds/endpoints.
    """
    prereg_id = str(preregistration.get("preregistration_id"))
    authorized = bool(
        authorization.get("authorized") is True
        and authorization.get("preregistration_id") == prereg_id
        and authorization.get("one_time_holdout_open") is True
        and authorization.get("frozen_preregistration_commit")
    )
    if not authorized:
        return {
            "status": "type_i_holdout_not_opened",
            "preregistration_id": prereg_id,
            "reason": "explicit_one_time_authorization_missing",
            "holdout_opened": False,
        }

    boundary = _boundaries(terminal_bar_calibration)
    if boundary is None or terminal_bar_calibration.get("status") != "terminal_bar_calibration_holdout_sealed":
        return {
            "status": "type_i_holdout_not_opened",
            "preregistration_id": prereg_id,
            "reason": "m2_17_terminal_calibration_not_ready",
            "holdout_opened": False,
        }

    contrast = preregistration.get("primary_contrast") or {}
    exposure_name = str((contrast.get("exposure") or {}).get("name"))
    comparator_name = str((contrast.get("comparator") or {}).get("name"))
    test = preregistration.get("confirmatory_test") or {}
    z = float(test.get("z"))
    min_group = int(test.get("minimum_records_per_group"))

    events = _terminal_events(records, reaction_horizon=reaction_horizon)
    splits, purged = assign_purged_split(events, boundary)
    holdout = [
        row
        for row in splits["holdout"]
        if _t2_pending(row, landmark_bar=landmark_bar)
    ]
    exposure = [row for row in holdout if _belongs(row, exposure_name)]
    comparator = [row for row in holdout if _belongs(row, comparator_name)]
    overlap_ids = {
        (row.get("instrument_id"), row.get("signal_bar"), row.get("pattern_id"), row.get("source_scale"))
        for row in exposure
    } & {
        (row.get("instrument_id"), row.get("signal_bar"), row.get("pattern_id"), row.get("source_scale"))
        for row in comparator
    }
    if overlap_ids:
        raise RuntimeError("pre-registered Holdout groups are not mutually exclusive")

    exposure_summary = _group_summary(
        exposure, landmark_bar=landmark_bar, reaction_horizon=reaction_horizon
    )
    comparator_summary = _group_summary(
        comparator, landmark_bar=landmark_bar, reaction_horizon=reaction_horizon
    )
    floor_ok = bool(
        exposure_summary["records"] >= min_group
        and comparator_summary["records"] >= min_group
    )

    interval = None
    effect = None
    if exposure_summary["endpoint_rate"] is not None and comparator_summary["endpoint_rate"] is not None:
        effect = float(exposure_summary["endpoint_rate"]) - float(comparator_summary["endpoint_rate"])
    if floor_ok:
        lower, upper = newcombe_difference_interval(
            int(exposure_summary["endpoint_hits"]),
            int(exposure_summary["records"]),
            int(comparator_summary["endpoint_hits"]),
            int(comparator_summary["records"]),
            z=z,
        )
        interval = {"lower": lower, "upper": upper}
        result = "confirmed" if lower > 0.0 else "not_confirmed"
    else:
        result = "inconclusive"

    return {
        "status": "type_i_holdout_evaluated_once",
        "preregistration_id": prereg_id,
        "authorization_id": authorization.get("authorization_id"),
        "frozen_preregistration_commit": authorization.get("frozen_preregistration_commit"),
        "holdout_opened": True,
        "holdout_total_m2_17_records": len(splits["holdout"]),
        "holdout_pending_t2_at_t5": len(holdout),
        "purged_records": len(purged),
        "primary_contrast": {
            "exposure_name": exposure_name,
            "comparator_name": comparator_name,
            "exposure": exposure_summary,
            "comparator": comparator_summary,
            "absolute_rate_difference": effect,
            "newcombe_95_ci": interval,
            "minimum_records_per_group": min_group,
            "sample_floor_ok": floor_ok,
            "result": result,
        },
        "secondary_diagnostics": {
            "role": "descriptive_only_cannot_rescue_primary_test",
            "groups": _descriptive_diagnostics(
                exposure,
                comparator,
                landmark_bar=landmark_bar,
                reaction_horizon=reaction_horizon,
            ),
        },
        "multiplicity": {
            "primary_tests_run": 1,
            "alternate_thresholds_searched": False,
            "alternate_endpoints_searched": False,
        },
        "policy_frozen": False,
        "interpretation": "Historical one-time confirmatory evidence on the frozen research Holdout; not a return forecast or trading recommendation.",
    }
