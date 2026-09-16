from htcn.harmonic.models import Pivot, PivotKind
from htcn.harmonic.pivots import visible_confirmed_pivots


def test_later_same_kind_replacement_does_not_erase_earlier_live_pivot() -> None:
    events = [
        Pivot(index=2, price=10.0, kind=PivotKind.LOW, scale=2, confirmed_at=4),
        Pivot(index=5, price=8.0, kind=PivotKind.LOW, scale=2, confirmed_at=7),
        Pivot(index=8, price=15.0, kind=PivotKind.HIGH, scale=2, confirmed_at=10),
    ]

    at_6 = visible_confirmed_pivots(events, cutoff=6)
    assert [(pivot.index, pivot.price) for pivot in at_6] == [(2, 10.0)]

    at_7 = visible_confirmed_pivots(events, cutoff=7)
    assert [(pivot.index, pivot.price) for pivot in at_7] == [(5, 8.0)]

    at_10 = visible_confirmed_pivots(events, cutoff=10)
    assert [(pivot.index, pivot.price) for pivot in at_10] == [(5, 8.0), (8, 15.0)]
