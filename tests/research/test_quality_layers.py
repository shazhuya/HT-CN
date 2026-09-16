from __future__ import annotations

from htcn.research.quality_gate import build_gate_library
from htcn.research.quality_layers import (
    classify_gate_layer,
    gate_generalization_diagnostics,
    pattern_family,
)


THRESHOLDS = {
    "prz_width_ratio": [0.10, 0.20, 0.30],
    "distance_to_prz_ratio": [0.10, 0.20, 0.30],
    "confirmation_lag_bars": [3, 5, 8],
}


def _spec(name: str):
    return {spec.name: spec for spec in build_gate_library(THRESHOLDS)}[name]


def _row(
    *,
    pattern: str,
    scale: int,
    width: float,
    touch: bool,
    retired: bool,
) -> dict:
    return {
        "instrument_id": "TEST",
        "signal_trade_date": "2025-01-01",
        "pattern_id": pattern,
        "schema": "test",
        "direction": "bullish",
        "source_scale": scale,
        "scale_support_count": 1,
        "confirmation_lag_bars": 3,
        "prz_width_ratio": width,
        "distance_to_prz_ratio": 0.15,
        "source_tolerance_used": False,
        "touch_before_retirement": touch,
        "bars_to_first_future_prz_touch": 8 if touch else None,
        "completion_before_retirement": False,
        "bars_to_completion_confirmation": None,
        "bars_to_frontier_retirement": 12 if retired else None,
    }


def _balanced_rows() -> list[dict]:
    rows: list[dict] = []
    for pattern, scale in (("abcd", 3), ("bat", 5), ("shark", 8)):
        for _ in range(20):
            rows.append(
                _row(
                    pattern=pattern,
                    scale=scale,
                    width=0.05,
                    touch=True,
                    retired=False,
                )
            )
        for _ in range(20):
            rows.append(
                _row(
                    pattern=pattern,
                    scale=scale,
                    width=0.25,
                    touch=False,
                    retired=True,
                )
            )
    return rows


def test_gate_semantics_are_separated() -> None:
    assert classify_gate_layer(_spec("narrow_prz_q1")) == "quality"
    assert classify_gate_layer(_spec("near_prz_q1")) == "readiness"
    assert classify_gate_layer(_spec("near_fast_q2")) == "readiness"
    assert classify_gate_layer(_spec("scale_ge8")) == "context"
    assert classify_gate_layer(_spec("scale8_narrow_q2")) == "mixed"
    assert classify_gate_layer(_spec("canonical_near_q2")) == "mixed"


def test_pattern_family_mapping_keeps_carney_schemas_distinct() -> None:
    assert pattern_family("abcd") == "ABCD"
    assert pattern_family("bat") == "XABCD"
    assert pattern_family("deep_crab") == "XABCD"
    assert pattern_family("shark") == "SHARK"
    assert pattern_family("five_zero") == "FIVE_ZERO"


def test_universal_quality_rejects_pattern_concentration() -> None:
    train = []
    validation = []
    for _ in range(50):
        train.append(_row(pattern="abcd", scale=3, width=0.05, touch=True, retired=False))
        validation.append(_row(pattern="abcd", scale=3, width=0.05, touch=True, retired=False))
    for pattern, scale in (("bat", 5), ("shark", 8)):
        for _ in range(6):
            train.append(_row(pattern=pattern, scale=scale, width=0.05, touch=True, retired=False))
            validation.append(_row(pattern=pattern, scale=scale, width=0.05, touch=True, retired=False))
    for pattern, scale in (("abcd", 3), ("bat", 5), ("shark", 8)):
        for _ in range(20):
            train.append(_row(pattern=pattern, scale=scale, width=0.25, touch=False, retired=True))
            validation.append(_row(pattern=pattern, scale=scale, width=0.25, touch=False, retired=True))

    report = gate_generalization_diagnostics(
        train,
        validation,
        _spec("narrow_prz_q1"),
        robust=True,
    )
    assert report["semantic_layer"] == "quality"
    assert report["pattern_generalization_ok"] is False
    assert report["universal_quality_candidate"] is False


def test_balanced_quality_can_pass_generalization_guard() -> None:
    train = _balanced_rows()
    validation = _balanced_rows()
    report = gate_generalization_diagnostics(
        train,
        validation,
        _spec("narrow_prz_q1"),
        robust=True,
    )
    assert report["pattern_generalization_ok"] is True
    assert report["family_generalization_ok"] is True
    assert report["scale_generalization_ok"] is True
    assert report["universal_quality_candidate"] is True
