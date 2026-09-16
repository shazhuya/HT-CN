import pytest

from htcn.harmonic.evaluator import evaluate_xabcd
from htcn.harmonic.models import HarmonicPoint, PatternState
from htcn.harmonic.rules import CARNEY_RULES


def _points(prices: tuple[float, float, float, float, float]) -> tuple[HarmonicPoint, ...]:
    labels = ("X", "A", "B", "C", "D")
    return tuple(
        HarmonicPoint(label, index * 10, price)
        for index, (label, price) in enumerate(zip(labels, prices))
    )


# Synthetic geometry fixtures only; not backtest evidence or textbook Golden Cases.
# They now deliberately sit on/near source-listed discrete harmonic ratios instead of merely
# falling somewhere inside a broad min/max envelope.
GOLDEN = {
    "gartley": (100.0, 200.0, 138.2, 183.2, 121.4),
    # B=.50, D=.886XA, C/AB≈.772 (near .786), BC=2.0.
    "bat": (100.0, 200.0, 150.0, 188.6, 111.4),
    # B=.382, D=1.0XA, C/AB=.786, BC≈3.058 (near 3.14). V2/V3 AB=CD
    # disagreement remains outside the hard identity gate.
    "alternate_bat": (100.0, 200.0, 161.8, 191.8252, 100.0),
    # B=.786, D=1.27XA, C/AB≈.616 (near .618), BC=2.0.
    "butterfly": (100.0, 200.0, 121.4, 169.8, 73.0),
    # B=.50, D=1.618XA, C/AB=.886, BC≈3.524 (near 3.618).
    "crab": (100.0, 200.0, 150.0, 194.3, 38.2),
    # B=.886, D=1.618XA, C/AB≈.511 (near .50), BC=2.618.
    "deep_crab": (100.0, 200.0, 111.4, 156.6410383189, 38.2),
}


@pytest.mark.parametrize("pattern_id", tuple(GOLDEN))
def test_source_shaped_golden_case_completes(pattern_id: str) -> None:
    result = evaluate_xabcd(CARNEY_RULES[pattern_id], _points(GOLDEN[pattern_id]))
    assert result.state is PatternState.COMPLETED, result.reasons
    assert all(check.passed for check in result.checks)


def test_core_golden_cases_are_identity_distinct() -> None:
    for expected, prices in GOLDEN.items():
        points = _points(prices)
        matches = [
            pattern_id
            for pattern_id in GOLDEN
            if evaluate_xabcd(CARNEY_RULES[pattern_id], points).passed
        ]
        assert expected in matches
        assert len(matches) == 1, (expected, matches)


def test_ratio_inside_broad_c_band_but_not_near_harmonic_family_is_rejected() -> None:
    # This candidate satisfies the old continuous Gartley envelopes:
    # B=.618, D=.786, C/AB=.75 lies between .382-.886 and BC≈1.36 lies between
    # 1.13-1.618. But .75 is not close enough to any source-listed C harmonic ratio.
    # The old engine accepted this class of arbitrary in-between values as harmonic.
    points = _points((100.0, 200.0, 138.2, 184.55, 121.4))
    result = evaluate_xabcd(CARNEY_RULES["gartley"], points)

    assert 0.382 <= result.metrics.c_ab.value <= 0.886
    c_band = next(check for check in result.checks if check.name == "c_ab")
    c_family = next(check for check in result.checks if check.name == "c_ab_harmonic_family")
    assert c_band.passed is True
    assert c_family.passed is False
    assert c_family.policy == "operational_match_to_source_family"
    assert result.state is PatternState.REJECTED
    assert any("source harmonic family" in reason for reason in result.reasons)


def test_prz_projects_discrete_bc_measurements_not_one_continuous_band() -> None:
    result = evaluate_xabcd(CARNEY_RULES["gartley"], _points(GOLDEN["gartley"]))
    bc_components = [
        component for component in result.prz.components if component.name.startswith("BC projection")
    ]

    assert [component.ratio_low for component in bc_components] == [1.13, 1.27, 1.414, 1.618]
    assert all(component.price_low == component.price_high for component in bc_components)
    assert not any(component.name == "BC projection envelope" for component in result.prz.components)
