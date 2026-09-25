from htcn.harmonic.recognition_oracle import (
    classify_xabcd_prices,
    oracle_pattern_ids,
)
from htcn.harmonic.recognition_stress import STANDARD_XABCD


def _mirror(prices: tuple[float, ...], axis: float = 300.0) -> tuple[float, ...]:
    return tuple(axis - value for value in prices)


def test_oracle_recovers_all_source_shaped_standard_patterns_both_directions() -> None:
    for pattern_id, prices in STANDARD_XABCD.items():
        assert pattern_id in oracle_pattern_ids(prices)
        assert pattern_id in oracle_pattern_ids(_mirror(prices))


def test_oracle_validates_nested_bat_exposed_by_gate1() -> None:
    prices = (100.0, 200.0, 150.0, 174.96699999999998, 111.4)

    matches = classify_xabcd_prices(prices)

    assert "bat" in {match.pattern_id for match in matches}
    bat = next(match for match in matches if match.pattern_id == "bat")
    assert abs(bat.metrics.b_xa - 0.5) < 1e-12
    assert abs(bat.metrics.d_xa - 0.886) < 1e-12


def test_oracle_rejects_independent_invalid_b_c_and_d_examples() -> None:
    gartley = STANDARD_XABCD["gartley"]
    x, a, b, c, d = gartley
    xa = a - x

    invalid_b = (x, a, a - xa * 0.70, c, d)
    invalid_c = (x, a, b, b + abs(a - b) * 0.66, d)
    invalid_d = (x, a, b, c, a - xa * 1.00)

    assert oracle_pattern_ids(invalid_b) == ()
    assert oracle_pattern_ids(invalid_c) == ()
    assert oracle_pattern_ids(invalid_d) == ()


def test_oracle_rejects_non_alternating_topology() -> None:
    assert oracle_pattern_ids((100.0, 200.0, 150.0, 140.0, 120.0)) == ()
