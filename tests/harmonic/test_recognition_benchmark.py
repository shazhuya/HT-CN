import pandas as pd

from htcn.harmonic.recognition_benchmark import (
    RecognitionPrediction,
    RecognitionTruth,
    diagnose_authoritative_truth,
    match_predictions,
    score_predictions,
)


def _truth(case_id: str = "case") -> RecognitionTruth:
    return RecognitionTruth(
        case_id=case_id,
        pattern_id="gartley",
        direction="bullish",
        labels=("X", "A", "B", "C", "D"),
        node_indices=(10, 20, 30, 40, 50),
    )


def _prediction(
    prediction_id: str,
    nodes=(10, 20, 30, 40, 50),
    pattern_id: str = "gartley",
) -> RecognitionPrediction:
    return RecognitionPrediction(
        prediction_id=prediction_id,
        pattern_id=pattern_id,
        direction="bullish",
        labels=("X", "A", "B", "C", "D"),
        node_indices=tuple(nodes),
    )


def test_one_truth_can_credit_at_most_one_prediction() -> None:
    truth = _truth()
    exact = _prediction("exact")
    duplicate = _prediction("duplicate")

    metrics = score_predictions([truth], [exact, duplicate], tolerance_bars=0)

    assert metrics.true_positive == 1
    assert metrics.false_positive == 1
    assert metrics.false_negative == 0
    assert metrics.precision == 0.5
    assert metrics.recall == 1.0


def test_tolerant_match_reports_node_error_without_calling_it_exact() -> None:
    truth = _truth()
    prediction = _prediction("shifted", nodes=(10, 21, 30, 39, 50))

    metrics = score_predictions([truth], [prediction], tolerance_bars=1)

    assert metrics.true_positive == 1
    assert metrics.exact_match_count == 0
    assert metrics.exact_match_rate == 0.0
    assert metrics.tolerant_match_rate == 1.0
    assert metrics.node_mae_bars == 0.4
    assert metrics.node_mae_by_label["A"] == 1.0
    assert metrics.node_mae_by_label["C"] == 1.0


def test_wrong_pattern_cannot_claim_true_positive() -> None:
    metrics = score_predictions(
        [_truth()],
        [_prediction("wrong", pattern_id="bat")],
        tolerance_bars=2,
    )

    assert metrics.true_positive == 0
    assert metrics.false_positive == 1
    assert metrics.false_negative == 1


def test_matching_prefers_exact_prediction_over_nearby_duplicate() -> None:
    truth = _truth()
    nearby = _prediction("a-nearby", nodes=(10, 20, 30, 41, 50))
    exact = _prediction("z-exact")

    matches = match_predictions(
        [truth],
        [nearby, exact],
        tolerance_bars=1,
    )

    assert len(matches) == 1
    assert matches[0].prediction.prediction_id == "z-exact"
    assert matches[0].exact


def _piecewise_gartley() -> pd.DataFrame:
    anchors = [
        (0, 120.0),
        (10, 100.0),
        (30, 200.0),
        (50, 138.2),
        (70, 183.2),
        (90, 121.4),
        (110, 141.4),
    ]
    closes = [0.0] * 111
    for (left_i, left_p), (right_i, right_p) in zip(
        anchors,
        anchors[1:],
        strict=False,
    ):
        for index in range(left_i, right_i + 1):
            fraction = (index - left_i) / (right_i - left_i)
            closes[index] = left_p + (right_p - left_p) * fraction
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * len(closes),
        }
    )


def test_authoritative_failure_diagnosis_accepts_known_gartley() -> None:
    truth = RecognitionTruth(
        case_id="gartley-controlled",
        pattern_id="gartley",
        direction="bullish",
        labels=("X", "A", "B", "C", "D"),
        node_indices=(10, 30, 50, 70, 90),
    )

    result = diagnose_authoritative_truth(
        _piecewise_gartley(),
        truth,
        scales=(3,),
    )

    assert result.stage == "accepted"
    assert result.scales_with_all_truth_nodes == (3,)
    assert result.scales_with_exact_candidate == (3,)
