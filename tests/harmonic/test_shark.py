import pytest

from htcn.harmonic.models import HarmonicPoint, PatternDirection, PatternState
from htcn.harmonic.shark import evaluate_shark, project_forming_shark


def _points(values):
    return tuple(
        HarmonicPoint(label=label, index=index, price=price)
        for index, (label, price) in enumerate(values)
    )


def test_bullish_shark_source_geometry_passes():
    points = _points((("0", 100.0), ("X", 120.0), ("A", 110.0), ("B", 125.0), ("C", 100.0)))
    result = evaluate_shark(points)

    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BULLISH
    assert 0.382 <= result.metrics.a_0x.value <= 0.618
    assert 1.13 <= result.metrics.b_xa.value <= 1.618
    assert 1.618 <= result.metrics.c_ab.value <= 2.24
    assert 0.886 <= result.metrics.c_0b.value <= 1.13
    assert result.prz.price_low <= 100.0 <= result.prz.component_price_high
    assert result.target_50 > points[-1].price
    assert result.initial_target == pytest.approx(result.target_50)
    assert result.initial_target_basis == "50_percent"


def test_bearish_shark_source_geometry_passes_and_first_target_is_direction_safe():
    points = _points((("0", 120.0), ("X", 100.0), ("A", 110.0), ("B", 95.0), ("C", 120.0)))
    result = evaluate_shark(points)

    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BEARISH
    assert result.target_50 < points[-1].price
    assert result.initial_target == pytest.approx(result.target_50)
    assert result.initial_target_basis == "50_percent"


def test_shark_reciprocal_abcd_can_be_the_first_5_0_measurement():
    # Construct a valid bullish Shark where C/AB=2.20.  The 50% BC reaction therefore
    # spans 1.10*AB, so the equal-length Reciprocal AB=CD at 1.00*AB is encountered first.
    # A/0X is exactly 0.382 and B/XA is 1.13; C/0B remains inside 0.886-1.13.
    x_price = 120.0
    xa = 10.0
    zero_price = x_price - xa / 0.382
    a_price = x_price - xa
    ab = 1.13 * xa
    b_price = a_price + ab
    bc = 2.20 * ab
    c_price = b_price - bc
    points = _points((("0", zero_price), ("X", x_price), ("A", a_price), ("B", b_price), ("C", c_price)))

    result = evaluate_shark(points)

    assert result.state is PatternState.COMPLETED, result.reasons
    assert result.metrics.a_0x.value == pytest.approx(0.382)
    assert result.metrics.b_xa.value == pytest.approx(1.13)
    assert result.metrics.c_ab.value == pytest.approx(2.20)
    assert 0.886 <= result.metrics.c_0b.value <= 1.13
    assert abs(result.reciprocal_abcd_target - c_price) < abs(result.target_50 - c_price)
    assert result.initial_target == pytest.approx(result.reciprocal_abcd_target)
    assert result.initial_target_basis == "reciprocal_abcd"


def test_shark_rejects_missing_extreme_impulse():
    points = _points((("0", 100.0), ("X", 120.0), ("A", 110.0), ("B", 125.0), ("C", 105.0)))
    result = evaluate_shark(points)

    assert result.state is PatternState.REJECTED
    assert any("C/AB" in reason or "C/0B" in reason for reason in result.reasons)


def test_forming_shark_projects_c_prz_from_0xab_frontier():
    points = _points((("0", 100.0), ("X", 120.0), ("A", 110.0), ("B", 125.0)))
    projection = project_forming_shark(points)

    assert projection is not None
    assert projection.direction is PatternDirection.BULLISH
    assert projection.prz.price_low > 0
    assert projection.prz.price_low <= projection.prz.price_high
