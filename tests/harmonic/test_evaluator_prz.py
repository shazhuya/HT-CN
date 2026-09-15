import pytest

from htcn.harmonic.evaluator import evaluate_xabcd, measure_xabcd
from htcn.harmonic.models import HarmonicPoint, PatternDirection, PatternState
from htcn.harmonic.prz import build_xabcd_prz
from htcn.harmonic.rules import CARNEY_RULES


def _bullish_gartley() -> tuple[HarmonicPoint, ...]:
    # XA=100; AB=61.8; CD=61.8; AD/XA=0.786; CD/BC=1.3733.
    return (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 10, 200.0),
        HarmonicPoint("B", 20, 138.2),
        HarmonicPoint("C", 30, 183.2),
        HarmonicPoint("D", 40, 121.4),
    )


def _bearish_gartley() -> tuple[HarmonicPoint, ...]:
    return (
        HarmonicPoint("X", 0, 200.0),
        HarmonicPoint("A", 10, 100.0),
        HarmonicPoint("B", 20, 161.8),
        HarmonicPoint("C", 30, 116.8),
        HarmonicPoint("D", 40, 178.6),
    )


def test_measure_xabcd_uses_price_leg_lengths() -> None:
    metrics = measure_xabcd(_bullish_gartley())
    assert metrics.b_xa.value == pytest.approx(0.618)
    assert metrics.cd_ab.value == pytest.approx(1.0)
    assert metrics.d_xa.value == pytest.approx(0.786)
    assert metrics.bc_projection.value == pytest.approx(61.8 / 45.0)


def test_exact_bullish_gartley_completes() -> None:
    result = evaluate_xabcd(CARNEY_RULES["gartley"], _bullish_gartley())
    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BULLISH
    assert not result.reasons
    assert all(check.passed for check in result.checks)


def test_exact_bearish_gartley_completes() -> None:
    result = evaluate_xabcd(CARNEY_RULES["gartley"], _bearish_gartley())
    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BEARISH


def test_wrong_b_point_rejects_gartley() -> None:
    points = list(_bullish_gartley())
    points[2] = HarmonicPoint("B", 20, 150.0)
    result = evaluate_xabcd(CARNEY_RULES["gartley"], tuple(points))
    assert result.state is PatternState.REJECTED
    assert any(reason.startswith("b_xa=") for reason in result.reasons)


def test_forming_gartley_prz_contains_xa_completion() -> None:
    x, a, b, c, _ = _bullish_gartley()
    prz = build_xabcd_prz(CARNEY_RULES["gartley"], (x, a, b, c))
    xa_component = next(component for component in prz.components if component.name == "XA completion")
    assert xa_component.price_low == pytest.approx(121.4)
    assert xa_component.price_high == pytest.approx(121.4)
    assert prz.direction is PatternDirection.BULLISH


def test_non_xabcd_rules_cannot_enter_xabcd_prz_path() -> None:
    x, a, b, c, _ = _bullish_gartley()
    with pytest.raises(ValueError, match="not XABCD"):
        build_xabcd_prz(CARNEY_RULES["shark"], (x, a, b, c))
