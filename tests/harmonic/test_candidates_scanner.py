from htcn.harmonic.candidates import (
    iter_completed_xabcd_windows,
    iter_forming_xabc_windows,
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


def test_forming_scanner_uses_b_point_to_narrow_rule_families() -> None:
    window = next(iter(iter_forming_xabc_windows(_gartley_pivots()[:4])))
    patterns = project_forming_xabcd(window)
    ids = {pattern.pattern_id for pattern in patterns}
    assert "gartley" in ids
    assert "bat" not in ids
    assert "butterfly" not in ids


def test_completed_scanner_identifies_exact_gartley() -> None:
    window = next(iter(iter_completed_xabcd_windows(_gartley_pivots())))
    matches = classify_completed_xabcd(window)
    assert [match.pattern_id for match in matches] == ["gartley"]
