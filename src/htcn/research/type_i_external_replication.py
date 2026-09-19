from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from .type_i_confirmation import _terminal_events
from .type_i_holdout_eval import newcombe_difference_interval

DEFAULT_LANDMARK_BAR = 5
DEFAULT_REACTION_HORIZON = 20


def _bar_value(audit: dict[str, Any], key: str) -> int | None:
    value = audit.get(key)
    return None if value is None else int(value)


def _eligible_pending_t2(row: dict[str, Any], *, landmark_bar: int) -> bool:
    t2 = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_t2")
    return t2 is None or t2 > landmark_bar


def _belongs_exposure(row: dict[str, Any], *, landmark_bar: int) -> bool:
    exit_bar = _bar_value(
        row["terminal_bar_audit"], "bars_from_terminal_to_full_prz_exit"
    )
    return exit_bar is not None and 1 <= exit_bar <= landmark_bar


def _endpoint_hit(
    row: dict[str, Any],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> bool:
    t2 = _bar_value(row["terminal_bar_audit"], "bars_from_terminal_to_t2")
    return bool(t2 is not None and landmark_bar < t2 <= reaction_horizon)


def _summary(
    rows: Iterable[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    values = list(rows)
    hits = sum(
        _endpoint_hit(
            row,
            landmark_bar=landmark_bar,
            reaction_horizon=reaction_horizon,
        )
        for row in values
    )
    return {
        "records": len(values),
        "endpoint_hits": int(hits),
        "endpoint_rate": None if not values else hits / len(values),
    }


def _descriptive_breakdown(
    exposure: list[dict[str, Any]],
    comparator: list[dict[str, Any]],
    *,
    landmark_bar: int,
    reaction_horizon: int,
) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for dimension in ("pattern_family", "pattern_id", "direction", "source_scale"):
        values = sorted(
            {str(row.get(dimension)) for row in [*exposure, *comparator]}
        )
        rows: list[dict[str, Any]] = []
        for value in values:
            exp = [row for row in exposure if str(row.get(dimension)) == value]
            comp = [row for row in comparator if str(row.get(dimension)) == value]
            rows.append(
                {
                    "value": value,
                    "exposure": _summary(
                        exp,
                        landmark_bar=landmark_bar,
                        reaction_horizon=reaction_horizon,
                    ),
                    "comparator": _summary(
                        comp,
                        landmark_bar=landmark_bar,
                        reaction_horizon=reaction_horizon,
                    ),
                }
            )
        out[dimension] = rows
    return out


def evaluate_external_type_i_replication(
    records: Iterable[dict[str, Any]],
    preregistration: dict[str, Any],
    *,
    successful_symbols: int,
    requested_symbols: int,
) -> dict[str, Any]:
    """Evaluate exactly the frozen external Type-I replication contrast.

    The replication is intentionally simpler than the original calibration stack: the
    symbol universe is already disjoint and frozen, so every mature source-aligned
    Terminal Price Bar event from successfully fetched symbols is part of the external
    replication population. No threshold, endpoint, family, scale or direction is fitted
    to these outcomes.
    """

    if successful_symbols < 0 or requested_symbols < 1:
        raise ValueError("invalid replication coverage counts")
    if successful_symbols > requested_symbols:
        raise ValueError("successful_symbols cannot exceed requested_symbols")

    dataset = preregistration.get("replication_dataset") or {}
    endpoint = preregistration.get("endpoint") or {}
    test = preregistration.get("confirmatory_test") or {}
    contrast = preregistration.get("primary_contrast") or {}

    landmark_bar = int(endpoint.get("landmark_bar") or DEFAULT_LANDMARK_BAR)
    reaction_horizon = int(
        endpoint.get("reaction_horizon_bars") or DEFAULT_REACTION_HORIZON
    )
    if landmark_bar < 1 or reaction_horizon <= landmark_bar:
        raise ValueError("invalid preregistered endpoint window")

    exposure_name = str((contrast.get("exposure") or {}).get("name"))
    comparator_name = str((contrast.get("comparator") or {}).get("name"))
    if exposure_name != "full_prz_exit_by_t5":
        raise ValueError("unsupported replication exposure")
    if comparator_name != "no_full_exit_by_t5":
        raise ValueError("unsupported replication comparator")

    coverage_min = int(dataset.get("minimum_successful_symbols") or 0)
    minimum_group = int(test.get("minimum_records_per_group") or 0)
    z = float(test.get("z") or 0.0)
    if coverage_min < 1 or minimum_group < 1 or z <= 0:
        raise ValueError("invalid preregistered confirmatory test")

    terminal_events = _terminal_events(records, reaction_horizon=reaction_horizon)
    eligible = [
        row
        for row in terminal_events
        if _eligible_pending_t2(row, landmark_bar=landmark_bar)
    ]
    exposure = [
        row for row in eligible if _belongs_exposure(row, landmark_bar=landmark_bar)
    ]
    comparator = [
        row for row in eligible if not _belongs_exposure(row, landmark_bar=landmark_bar)
    ]

    exposure_summary = _summary(
        exposure,
        landmark_bar=landmark_bar,
        reaction_horizon=reaction_horizon,
    )
    comparator_summary = _summary(
        comparator,
        landmark_bar=landmark_bar,
        reaction_horizon=reaction_horizon,
    )

    coverage_ok = successful_symbols >= coverage_min
    sample_floor_ok = bool(
        exposure_summary["records"] >= minimum_group
        and comparator_summary["records"] >= minimum_group
    )

    effect: float | None = None
    interval: dict[str, float] | None = None
    if (
        exposure_summary["endpoint_rate"] is not None
        and comparator_summary["endpoint_rate"] is not None
    ):
        effect = float(exposure_summary["endpoint_rate"]) - float(
            comparator_summary["endpoint_rate"]
        )

    if coverage_ok and sample_floor_ok:
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

    instrument_counts = Counter(str(row.get("instrument_id")) for row in eligible)
    largest_symbol_records = max(instrument_counts.values(), default=0)
    largest_symbol_share = (
        None if not eligible else largest_symbol_records / len(eligible)
    )

    return {
        "status": "external_type_i_replication_evaluated_once",
        "preregistration_id": preregistration.get("preregistration_id"),
        "dataset_id": dataset.get("dataset_id"),
        "requested_symbols": int(requested_symbols),
        "successful_symbols": int(successful_symbols),
        "minimum_successful_symbols": coverage_min,
        "coverage_ok": bool(coverage_ok),
        "mature_terminal_events": len(terminal_events),
        "eligible_pending_t2_at_t5": len(eligible),
        "primary_contrast": {
            "exposure_name": exposure_name,
            "comparator_name": comparator_name,
            "exposure": exposure_summary,
            "comparator": comparator_summary,
            "absolute_rate_difference": effect,
            "newcombe_95_ci": interval,
            "minimum_records_per_group": minimum_group,
            "sample_floor_ok": sample_floor_ok,
            "result": result,
        },
        "concentration": {
            "eligible_symbols": len(instrument_counts),
            "largest_symbol_records": int(largest_symbol_records),
            "largest_symbol_share": largest_symbol_share,
        },
        "secondary_diagnostics": {
            "role": "descriptive_only_cannot_replace_primary_test",
            "groups": _descriptive_breakdown(
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
            "subgroup_results_can_replace_primary": False,
        },
        "identity": {
            "carney_geometry_changed": False,
            "prz_changed": False,
            "t5_threshold_fitted_on_replication": False,
            "endpoint_fitted_on_replication": False,
        },
        "interpretation": (
            "One-time historical external-instrument replication of the frozen M2.22 Type-I T+5 "
            "association. It is not a return probability, trading win rate, buy/sell rule, or "
            "modification of Carney geometry."
        ),
    }
