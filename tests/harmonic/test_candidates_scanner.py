from htcn.harmonic.candidates import (
    SwingWindow,
    iter_completed_xabcd_windows,
    iter_forming_xabc_windows,
    iter_swing_windows,
)
from htcn.harmonic.models import Pivot, PivotKind
from htcn.harmonic.scanner import classify_completed_xabcd, project_forming_xabcd


def _gartley_pivots() -> list[Pivot]:
    return [
        Pivot(index=0, price=100.0, kind=PivotKind.LOW, scale=2, confirmed_at=2),
        Pivot(index=10, price=200.0, kind=PivotKind.HIGH, scale=2, confirmed_at=12),
        Pivot(index=20, price=138.2, kind=PivotKind.LOW, scale=2, confirmed_at=22),
        Pivot(index=30, price=183.2, kind=PivotKind.HIGH, scale=2, confirmed_at=32),
        Pivot(index=40, price=121.4, kind=PivotKind.LOW, scale=2, confirmed_at=42),
    ]


def test_candidate_windows_do_not_assign_pattern_identity() -> None:
    forming = list(iter_forming_xabc_windows(_gartley_pivots()[:4]))
    completed = list(iter_completed_xabcd_windows(_gartley_pivots()))
    assert len(forming) == 1
    assert len(completed) == 1
    assert forming[0].scale == 2
    assert [point.label for point in forming[0].harmonic_points()] == ["X", "A", "B", "C"]
    assert [point.label for point in completed[0].harmonic_points()] == ["X", "A", "B", "C", "D"]


def test_forming_window_is_frontier_only_after_new_confirmed_pivot() -> None:
    pivots = _gartley_pivots()
    historical_xabc = list(iter_swing_windows(pivots, size=4))
    live_xabc = list(iter_forming_xabc_windows(pivots))

    assert len(historical_xabc) == 2
    assert len(live_xabc) == 1
    assert [pivot.index for pivot in live_xabc[0].pivots] == [10, 20, 30, 40]
    assert [pivot.index for pivot in historical_xabc[0].pivots] == [0, 10, 20, 30]


def test_forming_scanner_uses_b_and_c_points_to_narrow_rule_families() -> None:
    window = next(iter(iter_forming_xabc_windows(_gartley_pivots()[:4])))
    patterns = project_forming_xabcd(window)
    ids = {pattern.pattern_id for pattern in patterns}
    assert "gartley" in ids
    assert "bat" not in ids
    assert "butterfly" not in ids
    gartley = next(pattern for pattern in patterns if pattern.pattern_id == "gartley")
    assert abs(gartley.c_ab - (45.0 / 61.8)) < 1e-12


def test_forming_scanner_rejects_source_invalid_c_retracement() -> None:
    # B is an exact Gartley 0.618 XA retracement, but C retraces only ~0.19 of AB,
    # below the source-backed 0.382 minimum. It must not project a Gartley PRZ.
    pivots = [
        Pivot(index=0, price=100.0, kind=PivotKind.LOW, scale=2, confirmed_at=2),
        Pivot(index=10, price=200.0, kind=PivotKind.HIGH, scale=2, confirmed_at=12),
        Pivot(index=20, price=138.2, kind=PivotKind.LOW, scale=2, confirmed_at=22),
        Pivot(index=30, price=150.0, kind=PivotKind.HIGH, scale=2, confirmed_at=32),
    ]
    window = SwingWindow(scale=2, pivots=tuple(pivots))
    ids = {pattern.pattern_id for pattern in project_forming_xabcd(window)}
    assert "gartley" not in ids


def test_completed_scanner_identifies_exact_gartley() -> None:
    window = next(iter(iter_completed_xabcd_windows(_gartley_pivots())))
    matches = classify_completed_xabcd(window)
    assert [match.pattern_id for match in matches] == ["gartley"]


def test_source_conflict_alternate_bat_is_fail_closed_by_default() -> None:
    pivots = [
        Pivot(index=0, price=100.0, kind=PivotKind.LOW, scale=2, confirmed_at=2),
        Pivot(index=10, price=200.0, kind=PivotKind.HIGH, scale=2, confirmed_at=12),
        Pivot(index=20, price=161.8, kind=PivotKind.LOW, scale=2, confirmed_at=22),
        Pivot(index=30, price=191.8252, kind=PivotKind.HIGH, scale=2, confirmed_at=32),
        Pivot(index=40, price=100.0, kind=PivotKind.LOW, scale=2, confirmed_at=42),
    ]
    window = SwingWindow(scale=2, pivots=tuple(pivots))

    production = classify_completed_xabcd(window)
    research = classify_completed_xabcd(
        window,
        include_source_conflict_patterns=True,
    )

    assert production == ()
    assert [match.pattern_id for match in research] == ["alternate_bat"]
