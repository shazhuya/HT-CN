from __future__ import annotations

from htcn.research.quality_gate import evaluate_gate_library


def _row(*, touch: bool, retired: bool, scale: int, support: int, width: float, distance: float, lag: int, tolerance: bool = False) -> dict:
    return {
        "source_scale": scale,
        "scale_support_count": support,
        "prz_width_ratio": width,
        "distance_to_prz_ratio": distance,
        "confirmation_lag_bars": lag,
        "source_tolerance_used": tolerance,
        "touch_before_retirement": touch,
        "bars_to_first_future_prz_touch": 8 if touch else None,
        "completion_before_retirement": False,
        "bars_to_completion_confirmation": None,
        "bars_to_frontier_retirement": 12 if retired else None,
    }


def test_quality_gate_uses_train_thresholds_and_confirms_same_direction() -> None:
    train = []
    validation = []
    # Good cohort: larger scales, narrow PRZ, close to PRZ, fast confirmation.
    for _ in range(30):
        train.append(_row(touch=True, retired=False, scale=8, support=2, width=0.05, distance=0.04, lag=3))
    for _ in range(30):
        train.append(_row(touch=False, retired=True, scale=3, support=1, width=0.30, distance=0.40, lag=12, tolerance=True))
    for _ in range(12):
        validation.append(_row(touch=True, retired=False, scale=8, support=2, width=0.06, distance=0.05, lag=4))
    for _ in range(12):
        validation.append(_row(touch=False, retired=True, scale=3, support=1, width=0.35, distance=0.45, lag=13, tolerance=True))

    thresholds = {
        "prz_width_ratio": [0.08, 0.18, 0.30],
        "distance_to_prz_ratio": [0.08, 0.20, 0.40],
        "confirmation_lag_bars": [4, 8, 12],
    }
    report = evaluate_gate_library(train, validation, thresholds=thresholds)
    assert report["holdout_opened"] is False
    assert report["policy_frozen"] is False
    assert "scale_ge8" in report["strong_candidates"]
    assert "narrow_prz_q1" in report["strong_candidates"]


def test_quality_gate_does_not_promote_small_validation_samples() -> None:
    train = [_row(touch=True, retired=False, scale=8, support=2, width=0.05, distance=0.05, lag=3) for _ in range(30)]
    train += [_row(touch=False, retired=True, scale=3, support=1, width=0.30, distance=0.40, lag=12) for _ in range(30)]
    validation = [_row(touch=True, retired=False, scale=8, support=2, width=0.05, distance=0.05, lag=3) for _ in range(5)]
    validation += [_row(touch=False, retired=True, scale=3, support=1, width=0.30, distance=0.40, lag=12) for _ in range(5)]
    thresholds = {
        "prz_width_ratio": [0.08, 0.18, 0.30],
        "distance_to_prz_ratio": [0.08, 0.20, 0.40],
        "confirmation_lag_bars": [4, 8, 12],
    }
    report = evaluate_gate_library(train, validation, thresholds=thresholds)
    assert report["strong_candidates"] == []
