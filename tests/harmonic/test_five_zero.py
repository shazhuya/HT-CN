from htcn.harmonic.five_zero import evaluate_five_zero, project_forming_five_zero
from htcn.harmonic.models import HarmonicPoint, PatternDirection, PatternState


def _points(values):
    return tuple(
        HarmonicPoint(label=label, index=index, price=price)
        for index, (label, price) in enumerate(values)
    )


def test_bullish_five_zero_source_geometry_passes():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 150.0), ("D", 120.0)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BULLISH
    assert result.metrics.b_xa.value == 1.5
    assert result.metrics.c_ab.value == 2.0
    assert result.metrics.d_bc.value == 0.5
    assert result.metrics.cd_ab.value == 1.0
    assert result.reciprocal_inside_execution_band
    assert result.completion_class == "volume2_50"


def test_bearish_five_zero_source_geometry_passes():
    points = _points((("X", 120.0), ("A", 100.0), ("B", 130.0), ("C", 70.0), ("D", 100.0)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BEARISH
    assert result.reciprocal_inside_execution_band


def test_five_zero_rejects_c_leg_below_mandatory_1618():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 135.0), ("D", 112.5)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.REJECTED
    assert any("C/AB" in reason for reason in result.reasons)


def test_forming_five_zero_projects_d_execution_zone():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 150.0)))
    projection = project_forming_five_zero(points)

    assert projection is not None
    assert projection.direction is PatternDirection.BULLISH
    assert projection.reciprocal_abcd_price == 120.0
    assert projection.prz.price_low <= 120.0 <= projection.prz.price_high
