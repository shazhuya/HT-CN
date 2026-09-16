from htcn.harmonic.engine import scan_pivots
from htcn.harmonic.models import Pivot, PivotKind


def _pivots(values, scale=3):
    return tuple(
        Pivot(
            index=index,
            price=price,
            kind=kind,
            scale=scale,
            confirmed_at=index,
        )
        for index, (price, kind) in enumerate(values)
    )


def test_engine_emits_completed_shark_from_dedicated_schema():
    pivots = _pivots(
        (
            (100.0, PivotKind.LOW),
            (120.0, PivotKind.HIGH),
            (110.0, PivotKind.LOW),
            (125.0, PivotKind.HIGH),
            (100.0, PivotKind.LOW),
        )
    )
    scan = scan_pivots({3: pivots})

    assert len(scan.shark_completed) == 1
    shark = scan.shark_completed[0]
    assert tuple(point.label for point in shark.points) == ("0", "X", "A", "B", "C")
    assert shark.evaluation.prz.price_low < shark.evaluation.prz.price_high


def test_default_engine_quarantines_source_conflict_five_zero():
    pivots = _pivots(
        (
            (100.0, PivotKind.LOW),
            (120.0, PivotKind.HIGH),
            (90.0, PivotKind.LOW),
            (150.0, PivotKind.HIGH),
            (120.0, PivotKind.LOW),
        )
    )
    scan = scan_pivots({3: pivots})

    assert scan.five_zero_completed == ()
    assert scan.five_zero_forming == ()


def test_research_opt_in_can_still_emit_five_zero_for_reconciliation():
    pivots = _pivots(
        (
            (100.0, PivotKind.LOW),
            (120.0, PivotKind.HIGH),
            (90.0, PivotKind.LOW),
            (150.0, PivotKind.HIGH),
            (120.0, PivotKind.LOW),
        )
    )
    scan = scan_pivots({3: pivots}, include_source_conflict_patterns=True)

    assert len(scan.five_zero_completed) == 1
    five_zero = scan.five_zero_completed[0]
    assert tuple(point.label for point in five_zero.points) == ("X", "A", "B", "C", "D")
    assert five_zero.evaluation.reciprocal_inside_execution_band


def test_engine_projects_only_frontier_advanced_forming_structures():
    shark_frontier = _pivots(
        (
            (100.0, PivotKind.LOW),
            (120.0, PivotKind.HIGH),
            (110.0, PivotKind.LOW),
            (125.0, PivotKind.HIGH),
        )
    )
    shark_scan = scan_pivots({3: shark_frontier})
    assert len(shark_scan.shark_forming) == 1

    five_zero_frontier = _pivots(
        (
            (100.0, PivotKind.LOW),
            (120.0, PivotKind.HIGH),
            (90.0, PivotKind.LOW),
            (150.0, PivotKind.HIGH),
        )
    )
    default_scan = scan_pivots({3: five_zero_frontier})
    assert default_scan.five_zero_forming == ()

    research_scan = scan_pivots(
        {3: five_zero_frontier},
        include_source_conflict_patterns=True,
    )
    assert len(research_scan.five_zero_forming) == 1
