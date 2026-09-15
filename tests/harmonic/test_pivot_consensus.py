from htcn.harmonic.models import Pivot, PivotKind
from htcn.harmonic.pivots import build_pivot_consensus


def _pivot(index: int, kind: PivotKind, scale: int, price: float) -> Pivot:
    return Pivot(index=index, price=price, kind=kind, scale=scale, confirmed_at=index + scale)


def test_pivot_consensus_groups_exact_index_and_kind_across_scales() -> None:
    pivots = {
        3: (
            _pivot(10, PivotKind.HIGH, 3, 120.0),
            _pivot(20, PivotKind.LOW, 3, 90.0),
        ),
        5: (
            _pivot(10, PivotKind.HIGH, 5, 120.0),
            _pivot(21, PivotKind.LOW, 5, 89.0),
        ),
        8: (_pivot(10, PivotKind.HIGH, 8, 120.0),),
    }
    consensus = build_pivot_consensus(pivots)
    assert consensus[(10, PivotKind.HIGH)] == (3, 5, 8)
    assert consensus[(20, PivotKind.LOW)] == (3,)
    assert consensus[(21, PivotKind.LOW)] == (5,)


def test_pivot_consensus_does_not_merge_opposite_kinds_same_index() -> None:
    pivots = {
        3: (_pivot(10, PivotKind.HIGH, 3, 120.0),),
        5: (_pivot(10, PivotKind.LOW, 5, 80.0),),
    }
    consensus = build_pivot_consensus(pivots)
    assert consensus[(10, PivotKind.HIGH)] == (3,)
    assert consensus[(10, PivotKind.LOW)] == (5,)
