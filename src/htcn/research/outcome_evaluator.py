from __future__ import annotations

from hashlib import sha256
import json
import math
from typing import Any

import pandas as pd

from htcn.harmonic.execution import observe_source_execution
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.prz import PRZComponent, PotentialReversalZone
from htcn.harmonic.source_lifecycle import derive_source_lifecycle

from .outcome_protocol import (
    canonical_outcome_protocol_fingerprint,
    load_outcome_protocol_v1,
    validate_outcome_protocol_v1,
)


OUTCOME_RESULT_SCHEMA_VERSION = 1
_REQUIRED_MARKET_COLUMNS = {
    "trade_date",
    "open",
    "high",
    "low",
    "close",
    "volume",
}
_FORMAL_PRICE_MODES = {"qfq", "qfq_carry_forward"}


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _validate_methodology_fingerprint(value: str) -> str:
    fingerprint = str(value or "")
    if len(fingerprint) != 64:
        raise ValueError("outcome evaluation requires methodology fingerprint")
    try:
        int(fingerprint, 16)
    except ValueError as exc:
        raise ValueError(
            "outcome methodology fingerprint must be hex"
        ) from exc
    return fingerprint


def _normalize_market_frame(
    frame: pd.DataFrame,
    *,
    outcome_as_of_trade_date: str,
) -> pd.DataFrame:
    missing = _REQUIRED_MARKET_COLUMNS.difference(frame.columns)
    if missing:
        raise ValueError(
            f"outcome market frame missing columns: {sorted(missing)}"
        )
    if frame.empty:
        raise ValueError("outcome market frame is empty")

    out = frame.copy()
    out["trade_date"] = pd.to_datetime(
        out["trade_date"],
        errors="raise",
    ).dt.normalize()
    as_of = pd.Timestamp(outcome_as_of_trade_date).normalize()
    out = out[out["trade_date"] <= as_of].copy()
    if out.empty:
        raise ValueError("outcome market frame has no bars through as-of")

    if out["trade_date"].duplicated().any():
        duplicates = (
            out.loc[out["trade_date"].duplicated(), "trade_date"]
            .dt.date.astype(str).tolist()
        )
        raise ValueError(
            f"outcome market frame has duplicate trade dates: {duplicates[:5]}"
        )

    for column in ("open", "high", "low", "close", "volume"):
        out[column] = pd.to_numeric(out[column], errors="raise")
        values = out[column].astype(float)
        if not values.map(math.isfinite).all():
            raise ValueError(
                f"outcome market frame has non-finite {column}"
            )
    for column in ("open", "high", "low", "close"):
        if (out[column].astype(float) <= 0).any():
            raise ValueError(
                f"outcome market frame has non-positive {column}"
            )
    if (out["volume"].astype(float) < 0).any():
        raise ValueError("outcome market frame has negative volume")

    out = out.sort_values("trade_date").reset_index(drop=True)
    return out


def _trade_date_index(frame: pd.DataFrame, trade_date: str) -> int | None:
    target = pd.Timestamp(trade_date).normalize()
    matches = frame.index[frame["trade_date"] == target].tolist()
    if not matches:
        return None
    if len(matches) != 1:
        raise ValueError(
            f"trade date {trade_date} is not unique in outcome frame"
        )
    return int(matches[0])


def _date_for_bar(frame: pd.DataFrame, bar: int | None) -> str | None:
    if bar is None:
        return None
    index = int(bar)
    if index < 0 or index >= len(frame):
        raise ValueError(f"outcome bar index outside frame: {index}")
    return pd.Timestamp(
        frame.iloc[index]["trade_date"]
    ).date().isoformat()


def _frozen_source_prz(
    *,
    pattern_id: str,
    direction: PatternDirection,
    source_low: float,
    source_high: float,
) -> PotentialReversalZone:
    component_name = "frozen prospective Source Raw PRZ"
    component = PRZComponent(
        name=component_name,
        price_low=source_low,
        price_high=source_high,
        ratio_low=1.0,
        ratio_high=1.0,
    )
    return PotentialReversalZone(
        pattern_id=pattern_id,
        direction=direction,
        components=(component,),
        source_prz_low=source_low,
        source_prz_high=source_high,
        source_prz_component_names=(component_name,),
        source_prz_defining_component=component_name,
        source_prz_selection_method="frozen_enrollment_source_prz",
        source_prz_source_refs=("m4-outcome-v1-enrollment-seed",),
        source_prz_note=(
            "Outcome reconstruction reuses the Source Raw PRZ frozen at "
            "prospective enrollment."
        ),
    )


def _enrollment_seed(
    candidate_summary: dict[str, Any],
) -> dict[str, Any]:
    seed = candidate_summary.get("enrollment_source_clock_seed")
    if not isinstance(seed, dict):
        raise ValueError("outcome candidate missing enrollment source-clock seed")

    required = (
        "pattern_id",
        "schema",
        "direction",
        "scale",
        "source_lifecycle_state",
        "source_prz_low",
        "source_prz_high",
        "source_signal_trade_date",
        "source_signal_clock_basis",
        "source_reaction_anchor_label",
        "source_reaction_anchor_price",
    )
    missing = [
        field
        for field in required
        if seed.get(field) is None or str(seed.get(field)) == ""
    ]
    if missing:
        raise ValueError(
            f"outcome candidate seed missing fields: {missing}"
        )

    schema = str(seed["schema"])
    expected_anchor = "B" if schema == "0XABC" else "A"
    if str(seed["source_reaction_anchor_label"]) != expected_anchor:
        raise ValueError(
            "outcome candidate reaction anchor conflicts with frozen schema"
        )
    if str(seed["source_signal_clock_basis"]) != (
        "last_frontier_pivot_confirmed_at=index+scale"
    ):
        raise ValueError("unsupported outcome source signal clock basis")

    source_low = float(seed["source_prz_low"])
    source_high = float(seed["source_prz_high"])
    anchor = float(seed["source_reaction_anchor_price"])
    if (
        not math.isfinite(source_low)
        or not math.isfinite(source_high)
        or source_low <= 0
        or source_high <= 0
        or source_low > source_high
        or not math.isfinite(anchor)
        or anchor <= 0
    ):
        raise ValueError("outcome candidate seed has invalid price values")
    return dict(seed)


def canonical_market_path_rows(
    frame: pd.DataFrame,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for row in frame.itertuples(index=False):
        rows.append({
            "trade_date": pd.Timestamp(row.trade_date).date().isoformat(),
            "open": float(row.open),
            "high": float(row.high),
            "low": float(row.low),
            "close": float(row.close),
            "volume": float(row.volume),
        })
    return rows


def canonical_market_path_hash(
    frame: pd.DataFrame,
    *,
    price_basis_id: str,
) -> str:
    payload = {
        "price_basis_id": str(price_basis_id),
        "rows": canonical_market_path_rows(frame),
    }
    return sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _window_excursion(
    frame: pd.DataFrame,
    *,
    terminal_bar: int,
    terminal_price: float,
    direction: PatternDirection,
    reaction_span: float,
    window: int,
) -> dict[str, Any]:
    available = max(0, len(frame) - (terminal_bar + 1))
    if available < window:
        return {
            "status": "immature",
            "window_traded_bars": int(window),
            "traded_bars_available": int(available),
            "starts_at": "T+1",
            "includes_terminal_bar": False,
            "metrics": None,
        }

    sample = frame.iloc[
        terminal_bar + 1 : terminal_bar + 1 + window
    ]
    if direction is PatternDirection.BULLISH:
        mfe = float(sample["high"].max()) - terminal_price
        mae = terminal_price - float(sample["low"].min())
    else:
        mfe = terminal_price - float(sample["low"].min())
        mae = float(sample["high"].max()) - terminal_price

    return {
        "status": "mature",
        "window_traded_bars": int(window),
        "traded_bars_available": int(available),
        "starts_at": "T+1",
        "includes_terminal_bar": False,
        "first_trade_date": pd.Timestamp(
            sample.iloc[0]["trade_date"]
        ).date().isoformat(),
        "last_trade_date": pd.Timestamp(
            sample.iloc[-1]["trade_date"]
        ).date().isoformat(),
        "metrics": {
            "mfe_price": mfe,
            "mae_price": mae,
            "mfe_terminal_pct": (mfe / terminal_price) * 100.0,
            "mae_terminal_pct": (mae / terminal_price) * 100.0,
            "mfe_reaction_span_units": mfe / reaction_span,
            "mae_reaction_span_units": mae / reaction_span,
        },
    }


def _empty_source_events() -> dict[str, Any]:
    return {
        "source_prz_entry_trade_date": None,
        "source_terminal_observed": False,
        "source_terminal_trade_date": None,
        "source_terminal_price": None,
        "target_382": None,
        "target_618": None,
        "type_i_early_window_mature": False,
        "type_i_early_result": "not_started",
        "type_i_382_first_hit_offset": None,
        "type_i_382_first_hit_trade_date": None,
        "type_i_618_first_hit_offset": None,
        "type_i_618_first_hit_trade_date": None,
        "reaction_only_later_382": False,
        "first_source_prz_exit_trade_date": None,
        "type_ii_retest_entry_trade_date": None,
        "type_ii_terminal_trade_date": None,
        "post_type_ii_reversal_exit_trade_date": None,
        "type_ii_price_structure_status": "not_observed_right_censored",
        "full_carney_type_ii_reversal_claim_allowed": False,
        "final_source_lifecycle_state": None,
    }


def _base_result(
    *,
    candidate_summary: dict[str, Any],
    outcome_as_of_trade_date: str,
    current_price_mode: str,
    current_price_basis_id: str,
    methodology_fingerprint: str,
    protocol: dict[str, Any],
    market_path: pd.DataFrame,
) -> dict[str, Any]:
    protocol_identity = validate_outcome_protocol_v1(protocol)
    candidate_key = str(candidate_summary.get("candidate_key") or "")
    instrument_id = str(candidate_summary.get("instrument_id") or "")
    enrolled = str(
        candidate_summary.get("outcome_enrollment_trade_date") or ""
    )
    if not candidate_key or not instrument_id or not enrolled:
        raise ValueError(
            "outcome candidate summary missing identity/enrollment fields"
        )
    if outcome_as_of_trade_date < enrolled:
        raise ValueError(
            "outcome as-of trade date precedes candidate enrollment"
        )

    path_dates = [
        pd.Timestamp(value).date().isoformat()
        for value in market_path["trade_date"].tolist()
    ]
    return {
        "schema_version": OUTCOME_RESULT_SCHEMA_VERSION,
        "candidate_key": candidate_key,
        "instrument_id": instrument_id,
        "outcome_enrollment_trade_date": enrolled,
        "outcome_as_of_trade_date": outcome_as_of_trade_date,
        "path_last_traded_date": (
            path_dates[-1] if path_dates else None
        ),
        "capture_methodology_fingerprint": methodology_fingerprint,
        "outcome_protocol_id": protocol_identity.protocol_id,
        "outcome_protocol_fingerprint": protocol_identity.fingerprint,
        "enrollment_price_mode": candidate_summary.get(
            "enrollment_price_mode"
        ),
        "enrollment_price_basis_id": candidate_summary.get(
            "enrollment_price_basis_id"
        ),
        "current_price_mode": current_price_mode,
        "current_price_basis_id": current_price_basis_id,
        "market_path_trade_dates": path_dates,
        "market_path_traded_bar_count": len(path_dates),
        "market_path_rows": canonical_market_path_rows(market_path),
        "market_path_sha256": canonical_market_path_hash(
            market_path,
            price_basis_id=current_price_basis_id,
        ),
        "status": "not_evaluated",
        "censoring_state": None,
        "source_events": _empty_source_events(),
        "descriptive_path_windows": {},
        "captured_pre_drift_facts": {
            "first_source_terminal_trade_date": (
                candidate_summary.get("first_source_terminal_trade_date")
            ),
            "first_lifecycle_state_observed": dict(
                candidate_summary.get(
                    "first_lifecycle_state_observed"
                ) or {}
            ),
        },
        "interpretation": {
            "evidence_only": True,
            "is_trade_instruction": False,
            "alpha_inference_allowed": False,
            "execution_pnl_computed": False,
            "win_loss_label_defined": False,
            "win_rate_computed": False,
            "benchmark_alpha_computed": False,
            "type_ii_price_structure_is_full_carney_confirmation": False,
            "shark_generic_type_i_is_management_target": False,
        },
    }


def evaluate_candidate_outcome(
    candidate_summary: dict[str, Any],
    market_frame: pd.DataFrame,
    *,
    outcome_as_of_trade_date: str,
    current_price_mode: str,
    current_price_basis_id: str,
    methodology_fingerprint: str,
    protocol: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if protocol is None:
        protocol, _ = load_outcome_protocol_v1()
    else:
        validate_outcome_protocol_v1(protocol)

    methodology = _validate_methodology_fingerprint(
        methodology_fingerprint
    )
    frame = _normalize_market_frame(
        market_frame,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
    )
    seed = _enrollment_seed(candidate_summary)
    signal_date = str(seed["source_signal_trade_date"])
    enrolled = str(
        candidate_summary.get("outcome_enrollment_trade_date") or ""
    )
    if not enrolled:
        raise ValueError("outcome candidate missing enrollment date")

    signal_bar = _trade_date_index(frame, signal_date)
    enrollment_bar = _trade_date_index(frame, enrolled)
    if signal_bar is None or enrollment_bar is None:
        result = _base_result(
            candidate_summary=candidate_summary,
            outcome_as_of_trade_date=outcome_as_of_trade_date,
            current_price_mode=current_price_mode,
            current_price_basis_id=current_price_basis_id,
            methodology_fingerprint=methodology,
            protocol=protocol,
            market_path=frame,
        )
        result["status"] = "unresolved_missing_market_data"
        result["censoring_state"] = "unresolved"
        result["missing_market_dates"] = [
            date_value
            for date_value, bar in (
                (signal_date, signal_bar),
                (enrolled, enrollment_bar),
            )
            if bar is None
        ]
        return result

    path = frame.iloc[signal_bar:].reset_index(drop=True)
    result = _base_result(
        candidate_summary=candidate_summary,
        outcome_as_of_trade_date=outcome_as_of_trade_date,
        current_price_mode=current_price_mode,
        current_price_basis_id=current_price_basis_id,
        methodology_fingerprint=methodology,
        protocol=protocol,
        market_path=path,
    )

    enrolled_mode = str(
        candidate_summary.get("enrollment_price_mode") or ""
    )
    enrolled_basis = str(
        candidate_summary.get("enrollment_price_basis_id") or ""
    )
    observed_basis_drift = int(
        candidate_summary.get("price_basis_drift_snapshot_count") or 0
    ) > 0
    basis_compatible = (
        current_price_mode in _FORMAL_PRICE_MODES
        and enrolled_mode in _FORMAL_PRICE_MODES
        and current_price_basis_id == enrolled_basis
        and not observed_basis_drift
    )
    if not basis_compatible:
        result["status"] = "unresolved_price_basis_interruption"
        result["censoring_state"] = "unresolved_after_drift"
        result["price_basis_compatible"] = False
        result["observed_price_basis_drift"] = observed_basis_drift
        return result

    result["price_basis_compatible"] = True
    result["observed_price_basis_drift"] = False

    direction = PatternDirection(str(seed["direction"]))
    source_low = float(seed["source_prz_low"])
    source_high = float(seed["source_prz_high"])
    anchor_price = float(seed["source_reaction_anchor_price"])
    prz = _frozen_source_prz(
        pattern_id=str(seed["pattern_id"]),
        direction=direction,
        source_low=source_low,
        source_high=source_high,
    )

    audit = observe_source_execution(
        frame,
        signal_bar=signal_bar,
        direction=direction,
        prz=prz,
        reaction_anchor_price=anchor_price,
        observation_end_bar=len(frame) - 1,
    )
    lifecycle = derive_source_lifecycle(frame, audit)

    source_events = _empty_source_events()
    source_events["source_prz_entry_trade_date"] = _date_for_bar(
        frame,
        audit.first_prz_entry_bar,
    )
    source_events["final_source_lifecycle_state"] = (
        lifecycle.state.value
    )

    if audit.terminal_bar is None or audit.terminal_price is None:
        result["status"] = "right_censored_ongoing"
        result["censoring_state"] = "terminal_not_observed"
        result["source_events"] = source_events
        return result

    terminal_bar = int(audit.terminal_bar)
    terminal_date = _date_for_bar(frame, terminal_bar)
    assert terminal_date is not None

    if terminal_date <= enrolled:
        result["status"] = "evidence_contradiction"
        result["censoring_state"] = None
        result["contradiction"] = (
            "reconstructed Source Terminal occurred on or before "
            "prospective outcome enrollment"
        )
        source_events["source_terminal_observed"] = True
        source_events["source_terminal_trade_date"] = terminal_date
        source_events["source_terminal_price"] = float(
            audit.terminal_price
        )
        source_events["target_382"] = audit.target_382
        source_events["target_618"] = audit.target_618
        result["source_events"] = source_events
        return result

    t1_offset = (
        None
        if lifecycle.type_i_t1_bar is None
        else int(lifecycle.type_i_t1_bar) - terminal_bar
    )
    t2_offset = (
        None
        if lifecycle.type_i_t2_bar is None
        else int(lifecycle.type_i_t2_bar) - terminal_bar
    )
    post_terminal_available = max(
        0,
        len(frame) - (terminal_bar + 1),
    )
    early_mature = post_terminal_available >= 5
    if t1_offset is not None and t1_offset <= 5:
        early_result = "confirmed_38_2_within_5"
    elif early_mature:
        early_result = "failed_38_2_within_5"
    else:
        early_result = "immature"

    type_ii_status = "not_observed_right_censored"
    if lifecycle.reversal_exit_after_type_ii_bar is not None:
        type_ii_status = "post_terminal_reversal_exit_observed"
    elif lifecycle.type_ii_terminal_bar is not None:
        type_ii_status = "terminal_side_retest_observed"
    elif lifecycle.type_ii_retest_entry_bar is not None:
        type_ii_status = "retest_forming"
    elif lifecycle.first_source_prz_exit_bar is not None:
        type_ii_status = "awaiting_secondary_retest"

    source_events.update({
        "source_terminal_observed": True,
        "source_terminal_trade_date": terminal_date,
        "source_terminal_price": float(audit.terminal_price),
        "target_382": audit.target_382,
        "target_618": audit.target_618,
        "type_i_early_window_mature": early_mature,
        "type_i_early_result": early_result,
        "type_i_382_first_hit_offset": t1_offset,
        "type_i_382_first_hit_trade_date": _date_for_bar(
            frame,
            lifecycle.type_i_t1_bar,
        ),
        "type_i_618_first_hit_offset": t2_offset,
        "type_i_618_first_hit_trade_date": _date_for_bar(
            frame,
            lifecycle.type_i_t2_bar,
        ),
        "reaction_only_later_382": (
            t1_offset is not None and t1_offset > 5
        ),
        "first_source_prz_exit_trade_date": _date_for_bar(
            frame,
            lifecycle.first_source_prz_exit_bar,
        ),
        "type_ii_retest_entry_trade_date": _date_for_bar(
            frame,
            lifecycle.type_ii_retest_entry_bar,
        ),
        "type_ii_terminal_trade_date": _date_for_bar(
            frame,
            lifecycle.type_ii_terminal_bar,
        ),
        "post_type_ii_reversal_exit_trade_date": _date_for_bar(
            frame,
            lifecycle.reversal_exit_after_type_ii_bar,
        ),
        "type_ii_price_structure_status": type_ii_status,
        "full_carney_type_ii_reversal_claim_allowed": False,
    })
    result["source_events"] = source_events

    reaction_span = abs(
        anchor_price - float(audit.terminal_price)
    )
    if reaction_span <= 0:
        raise ValueError(
            "outcome reaction span must be positive after terminal"
        )
    windows = (
        protocol.get("descriptive_path_metrics") or {}
    ).get("windows_traded_bars") or []
    result["descriptive_path_windows"] = {
        str(int(window)): _window_excursion(
            frame,
            terminal_bar=terminal_bar,
            terminal_price=float(audit.terminal_price),
            direction=direction,
            reaction_span=reaction_span,
            window=int(window),
        )
        for window in windows
    }

    result["status"] = "source_outcome_observed"
    result["censoring_state"] = (
        "type_ii_not_observed"
        if lifecycle.reversal_exit_after_type_ii_bar is None
        else None
    )
    result["source_reconstruction"] = {
        "source_execution_function": (
            "htcn.harmonic.execution.observe_source_execution"
        ),
        "lifecycle_function": (
            "htcn.harmonic.source_lifecycle.derive_source_lifecycle"
        ),
        "duplicate_formula_implementation_used": False,
    }
    result["outcome_protocol_fingerprint"] = (
        canonical_outcome_protocol_fingerprint(protocol)
    )
    return result
