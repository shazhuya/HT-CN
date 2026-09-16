import pandas as pd

from htcn.harmonic.models import Pivot, PivotKind
from htcn.harmonic.pivots import (
    collapse_same_kind_pivots,
    detect_confirmed_pivots,
    detect_multi_scale_pivots,
)


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "high": [10.0, 12.0, 11.0, 9.0, 10.0, 13.0, 12.0],
            "low": [9.0, 10.0, 8.0, 7.0, 8.0, 11.0, 10.0],
        }
    )


def test_confirmed_pivots_wait_for_right_side_bars() -> None:
    pivots = detect_confirmed_pivots(_frame(), left=1, right=1, scale=1)
    assert [(p.index, p.kind, p.confirmed_at) for p in pivots] == [
        (1, PivotKind.HIGH, 2),
        (3, PivotKind.LOW, 4),
        (5, PivotKind.HIGH, 6),
    ]


def test_flat_tops_are_not_emitted_as_duplicate_pivots() -> None:
    frame = pd.DataFrame(
        {
            "high": [10.0, 12.0, 12.0, 11.0],
            "low": [9.0, 10.0, 10.0, 9.5],
        }
    )
    pivots = detect_confirmed_pivots(frame, left=1, right=1, scale=1)
    assert not any(p.kind == PivotKind.HIGH for p in pivots)


def test_same_kind_nodes_keep_the_more_extreme_pivot() -> None:
    collapsed = collapse_same_kind_pivots(
        [
            Pivot(index=1, price=10.0, kind=PivotKind.HIGH, scale=2, confirmed_at=3),
            Pivot(index=2, price=12.0, kind=PivotKind.HIGH, scale=2, confirmed_at=4),
            Pivot(index=4, price=8.0, kind=PivotKind.LOW, scale=2, confirmed_at=6),
        ]
    )
    assert [(p.index, p.price, p.kind) for p in collapsed] == [
        (2, 12.0, PivotKind.HIGH),
        (4, 8.0, PivotKind.LOW),
    ]


def test_multi_scale_pivots_are_independent() -> None:
    result = detect_multi_scale_pivots(_frame(), scales=(1, 2))
    assert set(result) == {1, 2}
    assert all(p.scale == 1 for p in result[1])
    assert all(p.scale == 2 for p in result[2])
