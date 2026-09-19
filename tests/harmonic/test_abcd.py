import math

import pandas as pd

from htcn.harmonic.abcd import evaluate_abcd
from htcn.harmonic.engine import scan_pivots
from htcn.harmonic.lifecycle import audit_completed_reaction
from htcn.harmonic.models import HarmonicPoint, PatternDirection, Pivot, PivotKind


def _bullish_points():
    return (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 161.8),
        HarmonicPoint("D", 3, 61.8),
    )


def test_perfect_618_1618_equivalent_abcd_passes() -> None:
    evaluation = evaluate_abcd(_bullish_points())
    assert evaluation.passed is True
    assert evaluation.direction is PatternDirection.BULLISH
    assert math.isclose(evaluation.metrics.c_ab.value, 0.618, rel_tol=1e-9)
    assert math.isclose(evaluation.metrics.cd_ab.value, 1.0, rel_tol=1e-9)
    assert evaluation.reciprocal_c_target == 0.618
    assert evaluation.reciprocal_bc_target == 1.618
    assert evaluation.prz.price_low > 0
    assert evaluation.prz.width < 0.05


def test_382_retracement_selects_2618_reciprocal_when_it_converges() -> None:
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 138.2),
        HarmonicPoint("D", 3, 38.2),
    )
    evaluation = evaluate_abcd(points)
    assert evaluation.passed is True
    assert evaluation.reciprocal_c_target == 0.382
    assert evaluation.reciprocal_bc_target == 2.618


def test_wrong_bc_projection_or_non_equivalent_cd_rejects_abcd() -> None:
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 161.8),
        HarmonicPoint("D", 3, 80.0),
    )
    evaluation = evaluate_abcd(points)
    assert evaluation.passed is False
    assert any("CD/AB" in reason or "CD/BC" in reason for reason in evaluation.reasons)


def test_abcd_scans_as_dedicated_schema_without_five_pivot_xabcd() -> None:
    pivots = (
        Pivot(index=10, price=200.0, kind=PivotKind.HIGH, scale=5, confirmed_at=15),
        Pivot(index=20, price=100.0, kind=PivotKind.LOW, scale=5, confirmed_at=25),
        Pivot(index=30, price=161.8, kind=PivotKind.HIGH, scale=5, confirmed_at=35),
        Pivot(index=40, price=61.8, kind=PivotKind.LOW, scale=5, confirmed_at=45),
    )
    scan = scan_pivots({5: pivots}, max_completed=20)
    assert len(scan.abcd_completed) == 1
    match = scan.abcd_completed[0]
    assert match.pattern_id == "abcd"
    assert tuple(point.label for point in match.points) == ("A", "B", "C", "D")
    assert len(scan.completed) == 0


def test_reaction_audit_accepts_standalone_abcd_a_to_d_span() -> None:
    points = _bullish_points()
    evaluation = evaluate_abcd(points)
    frame = pd.DataFrame(
        {
            "close": [200, 100, 161.8, 61.8, 90, 120, 150],
            "high": [201, 101, 162, 63, 92, 122, 152],
            "low": [199, 99, 160, 60, 88, 118, 148],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=points,
        direction=PatternDirection.BULLISH,
        prz=evaluation.prz,
        rsi_period=3,
    )
    assert audit.d_index == 3
    assert audit.bars_observed == 3
    assert audit.target_382 > points[-1].price
    assert audit.bars_to_382 is not None
