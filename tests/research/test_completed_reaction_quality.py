from __future__ import annotations

from datetime import date, timedelta

from htcn.research.completed_reaction_quality import (
    build_completed_reaction_quality_report,
    learn_completed_reaction_thresholds,
)


def _row(
    index: int,
    *,
    width: float,
    geometry: float = 80.0,
    lag: int = 5,
    outcome_class: str = "no_t1_within_horizon",
    sealed: bool = False,
) -> dict:
    signal = date(2020, 1, 1) + timedelta(days=index * 10)
    observation_end = signal + timedelta(days=2)
    outcome = {"sealed": True} if sealed else {
        "outcome_class": outcome_class,
        "late_completion_signal": False,
        "available_future_bars_after_confirmation": 20,
    }
    return {
        "instrument_id": f"SSE.60{index:04d}",
        "pattern_id": "abcd",
        "pattern_family": "ABCD",
        "schema": "ABCD",
        "direction": "bullish",
        "source_scale": 5,
        "geometry_score": geometry,
        "source_tolerance_used": None,
        "confirmation_lag_bars": lag,
        "signal_bar": index * 10,
        "signal_trade_date": signal.isoformat(),
        "observation_end_trade_date": observation_end.isoformat(),
        "quality_at_signal": {
            "prz_width_ratio": width,
            "geometry_score": geometry,
            "source_tolerance_used": None,
        },
        "outcome": outcome,
    }


def _calibration() -> dict:
    def day(index: int) -> str:
        return (date(2020, 1, 1) + timedelta(days=index * 10)).isoformat()

    return {
        "status": "completed_reaction_calibration_holdout_sealed",
        "boundaries": {
            "train_end": day(14),
            "validation_start": day(15),
            "validation_end": day(21),
            "holdout_start": day(22),
        },
        "holdout": {
            "sealed": True,
            "records": 8,
            "signal_start": day(22),
            "signal_end": day(29),
            "outcomes_exposed": False,
        },
    }


def test_completed_quality_keeps_holdout_sealed_and_finds_consistent_narrow_prz() -> None:
    rows = []
    for index in range(15):
        narrow = index < 7
        rows.append(
            _row(
                index,
                width=0.01 if narrow else 0.05,
                outcome_class="t2_within_horizon" if narrow else "no_t1_within_horizon",
            )
        )
    for index in range(15, 22):
        narrow = index < 19
        rows.append(
            _row(
                index,
                width=0.01 if narrow else 0.05,
                outcome_class="t2_within_horizon" if narrow else "no_t1_within_horizon",
            )
        )
    rows.extend(_row(index, width=0.001, sealed=True) for index in range(22, 30))

    report = build_completed_reaction_quality_report(
        rows,
        _calibration(),
        minimum_train_gate=5,
        minimum_validation_gate=3,
    )

    assert report["status"] == "completed_reaction_quality_evidence_holdout_sealed"
    assert report["holdout"] == {"sealed": True, "records": 8, "outcomes_exposed": False}
    assert "t1_rate" not in report["holdout"]
    assert "narrow_prz_q1" in report["consistent_t1_candidates"]
    assert "narrow_prz_q1" in report["t2_corroborated_candidates"]
    assert report["thresholds"]["prz_width_q25"] == 0.01
    assert all(gate["eligible_for_policy_freeze"] is False for gate in report["gates"])


def test_numeric_thresholds_are_learned_from_train_only_and_preserve_zero_lag() -> None:
    train = [
        _row(index, width=float(index + 1), geometry=float(70 + index), lag=index % 4)
        for index in range(12)
    ]
    thresholds = learn_completed_reaction_thresholds(train)
    assert thresholds["prz_width_q25"] < thresholds["prz_width_q50"]
    assert thresholds["geometry_q50"] < thresholds["geometry_q75"]
    assert thresholds["confirmation_lag_q25"] >= 0


def test_completed_quality_refuses_to_research_when_calibration_sample_is_insufficient() -> None:
    calibration = {
        "status": "completed_reaction_sample_insufficient_holdout_sealed",
        "reason": "actionable_completed_reaction_sample_below_research_floor_after_purge",
        "holdout": {"sealed": True, "records": 4, "outcomes_exposed": False},
    }
    report = build_completed_reaction_quality_report([], calibration)
    assert report["status"] == "completed_reaction_quality_sample_insufficient_holdout_sealed"
    assert report["gates"] == []
    assert report["consistent_t1_candidates"] == []
    assert report["holdout"]["outcomes_exposed"] is False
