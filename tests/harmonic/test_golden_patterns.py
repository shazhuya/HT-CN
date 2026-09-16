import pytest

from htcn.harmonic.evaluator import evaluate_xabcd
from htcn.harmonic.models import HarmonicPoint, PatternState
from htcn.harmonic.rules import CARNEY_RULES


def _points(prices: tuple[float, float, float, float, float]) -> tuple[HarmonicPoint, ...]:
    labels = ("X", "A", "B", "C", "D")
    return tuple(HarmonicPoint(label, index * 10, price) for index, (label, price) in enumerate(zip(labels, prices)))


# These synthetic cases are not backtest evidence. They are geometry fixtures chosen so
# each structure satisfies its source-defined B/C/BC/XA relationships. They protect the
# identity engine from regressions while real-market Golden Cases are added separately.
GOLDEN = {
    "gartley": (100.0, 200.0, 138.2, 183.2, 121.4),
    # B=.50, D=.886XA, C/AB=.772, BC=2.0.
    "bat": (100.0, 200.0, 150.0, 188.6, 111.4),
    # B=.382, D=1.0XA, C/AB≈.756, BC=3.14. V2/V3 AB=CD disagreement
    # is intentionally not used as an identity gate.
    "alternate_bat": (100.0, 200.0, 161.8, 190.6785046729, 100.0),
    # B=.786, D=1.27XA, C/AB≈.616, BC=2.0.
    "butterfly": (100.0, 200.0, 121.4, 169.8, 73.0),
    # B=.50, D=1.618XA, C/AB≈.854, BC=3.618.
    "crab": (100.0, 200.0, 150.0, 192.7043544691, 38.2),
    # B=.886, D=1.618XA, C/AB≈.511, BC=2.618.
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
        # Alternate Bat may share broad complementary geometry with another family only if
        # future source rules explicitly allow it; today's frozen registry should distinguish it.
        assert expected in matches
        assert len(matches) == 1, (expected, matches)
