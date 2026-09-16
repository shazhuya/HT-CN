import pytest

import htcn.harmonic.evaluator as evaluator_module
from htcn.harmonic.evaluator import evaluate_xabcd, match_xabcd, measure_xabcd
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


def _bullish_crab_with_nonideal_abcd() -> tuple[HarmonicPoint, ...]:
    # XA=20, B/XA=.50, C/AB=.88, D/XA=1.618, BC projection≈3.541.
    # CD/AB≈3.116 is deliberately far from the common 1.0/1.27/1.618 variants.
    # The source defines a minimum AB=CD plus the defining XA/BC geometry, so this
    # remains an identity match while receiving a softer geometry score later.
    return (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 10, 120.0),
        HarmonicPoint("B", 20, 110.0),
        HarmonicPoint("C", 30, 118.8),
        HarmonicPoint("D", 40, 87.64),
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


def test_match_xabcd_passed_path_is_identical_to_full_evaluator() -> None:
    full = evaluate_xabcd(CARNEY_RULES["gartley"], _bullish_gartley())
    matched = match_xabcd(CARNEY_RULES["gartley"], _bullish_gartley())
    assert matched is not None
    assert matched.pattern_id == full.pattern_id
    assert matched.direction is full.direction
    assert matched.state is full.state
    assert matched.metrics == full.metrics
    assert matched.checks == full.checks
    assert matched.abcd_distance == full.abcd_distance
    assert matched.reasons == full.reasons
    assert matched.prz == full.prz


def test_match_xabcd_rejection_never_builds_prz(monkeypatch: pytest.MonkeyPatch) -> None:
    points = list(_bullish_gartley())
    points[2] = HarmonicPoint("B", 20, 150.0)

    def _unexpected_prz(*args: object, **kwargs: object) -> object:
        raise AssertionError("rejected Scanner candidate must not construct a PRZ")

    monkeypatch.setattr(evaluator_module, "build_xabcd_prz", _unexpected_prz)
    assert match_xabcd(CARNEY_RULES["gartley"], tuple(points)) is None


def test_wrong_b_point_rejects_gartley() -> None:
    points = list(_bullish_gartley())
    points[2] = HarmonicPoint("B", 20, 150.0)
    result = evaluate_xabcd(CARNEY_RULES["gartley"], tuple(points))
    assert result.state is PatternState.REJECTED
    assert any(reason.startswith("b_xa=") for reason in result.reasons)


def test_source_minimum_abcd_is_hard_but_preferred_variant_is_soft() -> None:
    result = evaluate_xabcd(CARNEY_RULES["crab"], _bullish_crab_with_nonideal_abcd())
    assert result.state is PatternState.COMPLETED
    assert result.metrics.cd_ab.value > 3.0
    assert result.abcd_distance > 0.5
    minimum = next(check for check in result.checks if check.name == "abcd_minimum")
    assert minimum.passed


def test_gartley_below_minimum_abcd_rejects_even_when_other_ratios_fit() -> None:
    points = (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 10, 120.0),
        HarmonicPoint("B", 20, 107.64),
        HarmonicPoint("C", 30, 113.10),
        HarmonicPoint("D", 40, 104.28),
    )
    result = evaluate_xabcd(CARNEY_RULES["gartley"], points)
    assert result.metrics.b_xa.value == pytest.approx(0.618)
    assert result.metrics.d_xa.value == pytest.approx(0.786)
    assert 1.13 <= result.metrics.bc_projection.value <= 1.618
    assert result.metrics.cd_ab.value < 1.0
    assert result.state is PatternState.REJECTED
    assert any("below source minimum" in reason for reason in result.reasons)


def test_gartley_prz_separates_component_envelope_ideal_core_and_source_raw_prz() -> None:
    x, a, b, c, _ = _bullish_gartley()
    prz = build_xabcd_prz(CARNEY_RULES["gartley"], (x, a, b, c))
    xa_component = next(component for component in prz.components if component.name == "XA completion")
    assert xa_component.price_low == pytest.approx(121.4)
    assert xa_component.price_high == pytest.approx(121.4)
    assert prz.direction is PatternDirection.BULLISH

    # The component envelope contains every stored discrete harmonic measurement/variant.
    # It remains audit data and is intentionally wider than the selected source zone.
    assert prz.component_envelope_low == pytest.approx(prz.component_price_low)
    assert prz.component_envelope_high == pytest.approx(prz.component_price_high)
    assert prz.component_envelope_low < prz.ideal_core_low
    assert prz.component_envelope_high > prz.ideal_core_high

    # The HT-CN ideal core remains a generic engineering convergence layer.
    assert prz.ideal_core_low <= xa_component.midpoint <= prz.ideal_core_high
    assert prz.price_low == pytest.approx(prz.ideal_core_low)
    assert prz.price_high == pytest.approx(prz.ideal_core_high)
    assert prz.width == pytest.approx(prz.ideal_core_width)

    # M2.27 freezes Gartley Raw PRZ membership independently from the ideal-core code path.
    assert prz.has_source_prz is True
    assert prz.source_prz_status == "frozen"
    assert prz.source_prz_component_names == (
        "XA completion",
        "BC projection x1.414",
        "AB=CD x1",
    )
    selected = [component for component in prz.components if component.name in prz.source_prz_component_names]
    assert prz.source_prz_low == pytest.approx(min(component.price_low for component in selected))
    assert prz.source_prz_high == pytest.approx(max(component.price_high for component in selected))
    assert prz.component_envelope_low < prz.source_prz_low
    assert prz.component_envelope_high > prz.source_prz_high


def test_non_xabcd_rules_cannot_enter_xabcd_prz_path() -> None:
    x, a, b, c, _ = _bullish_gartley()
    with pytest.raises(ValueError, match="not XABCD"):
        build_xabcd_prz(CARNEY_RULES["shark"], (x, a, b, c))
