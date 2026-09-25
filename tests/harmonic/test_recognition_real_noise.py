import pandas as pd

from htcn.harmonic.models import PivotKind
from htcn.harmonic.pivots import detect_multi_scale_pivots
from htcn.harmonic.recognition_real_noise import (
    NODE_INDICES,
    holdout_symbols,
    inject_pattern_into_real_background,
)


def _background(rows: int = 600) -> pd.DataFrame:
    close = [100.0 + index * 0.03 + ((index % 11) - 5) * 0.08 for index in range(rows)]
    open_ = [value * (1.0 + ((index % 5) - 2) * 0.0008) for index, value in enumerate(close)]
    high = [max(o, c) * 1.004 for o, c in zip(open_, close, strict=True)]
    low = [min(o, c) * 0.996 for o, c in zip(open_, close, strict=True)]
    return pd.DataFrame(
        {
            "open": open_,
            "high": high,
            "low": low,
            "close": close,
            "volume": [1000.0 + index for index in range(rows)],
        }
    )


def test_holdout_assignment_is_order_independent_and_fixed_size() -> None:
    symbols = [f"SSE.60{index:04d}" for index in range(20)]
    forward = holdout_symbols(symbols, count=4)
    backward = holdout_symbols(list(reversed(symbols)), count=4)

    assert forward == backward
    assert len(forward) == 4


def test_real_noise_injection_keeps_truth_nodes_exact_and_deterministic() -> None:
    first = inject_pattern_into_real_background(
        _background(),
        instrument_id="SSE.600000",
        pattern_id="gartley",
        direction="bullish",
        seed=12345,
        split="development",
    )
    second = inject_pattern_into_real_background(
        _background(),
        instrument_id="SSE.600000",
        pattern_id="gartley",
        direction="bullish",
        seed=12345,
        split="development",
    )

    assert first.truth.node_indices == NODE_INDICES
    assert first.frame.equals(second.frame)
    for index in NODE_INDICES:
        assert first.frame.loc[index, "open"] == first.frame.loc[index, "close"]
        assert first.frame.loc[index, "high"] == first.frame.loc[index, "close"]
        assert first.frame.loc[index, "low"] == first.frame.loc[index, "close"]


def test_real_noise_truth_nodes_are_actual_turning_pivots() -> None:
    for direction in ("bullish", "bearish"):
        case = inject_pattern_into_real_background(
            _background(),
            instrument_id="SSE.600000",
            pattern_id="gartley",
            direction=direction,
            seed=12345,
            split="development",
        )
        pivots = detect_multi_scale_pivots(case.frame, scales=(3,))[3]
        expected_kinds = (
            (PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW)
            if direction == "bullish"
            else (PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH)
        )
        observed = {(pivot.index, pivot.kind) for pivot in pivots}
        assert all(
            (index, kind) in observed
            for index, kind in zip(NODE_INDICES, expected_kinds, strict=True)
        )
