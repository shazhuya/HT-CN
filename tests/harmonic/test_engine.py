from htcn.harmonic.engine import scan_pivots
from htcn.harmonic.models import Pivot, PivotKind


def _gartley_pivots(scale: int = 5) -> list[Pivot]:
    # Exact bullish Gartley geometry:
    # X=100, A=120, B=107.64 (0.618 XA), C=116.64,
    # D=104.28 (0.786 XA), AB=CD, BC projection ~=1.373.
    prices = [100.0, 120.0, 107.64, 116.64, 104.28]
    kinds = [PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW, PivotKind.HIGH, PivotKind.LOW]
    return [
        Pivot(index=index * 10, price=price, kind=kind, scale=scale, confirmed_at=index * 10 + scale)
        for index, (price, kind) in enumerate(zip(prices, kinds))
    ]


def test_scan_pivots_finds_exact_gartley() -> None:
    scan = scan_pivots({5: _gartley_pivots()})
    gartleys = [match for match in scan.completed if match.pattern_id == "gartley"]
    assert len(gartleys) == 1
    match = gartleys[0]
    assert match.direction.value == "bullish"
    assert match.geometry_score >= 95
    assert match.conflict_key == (0, 10, 20, 30, 40)
    assert match.evaluation.prz.price_low > 0


def test_scan_pivots_keeps_forming_and_completed_separate() -> None:
    completed = _gartley_pivots()
    forming_only = completed[:-1]
    scan = scan_pivots({5: forming_only})
    assert scan.completed == ()
    assert any(match.pattern_id == "gartley" for match in scan.forming)
    assert all(match.state.value == "forming" for match in scan.forming)


def test_same_geometry_has_stable_conflict_key() -> None:
    scan = scan_pivots({5: _gartley_pivots()})
    assert scan.completed
    keys = {match.conflict_key for match in scan.completed}
    assert (0, 10, 20, 30, 40) in keys
