import pytest

from htcn.harmonic.ratios import leg_length, ratio_of_legs, reciprocal_bc_targets


def test_leg_length_is_direction_agnostic() -> None:
    assert leg_length(100.0, 130.0) == pytest.approx(30.0)
    assert leg_length(130.0, 100.0) == pytest.approx(30.0)


def test_ratio_of_legs_is_auditable() -> None:
    measured = ratio_of_legs(
        name="bc_over_ab",
        numerator_start=150.0,
        numerator_end=100.0,
        denominator_start=200.0,
        denominator_end=150.0,
    )
    assert measured.name == "bc_over_ab"
    assert measured.numerator == pytest.approx(50.0)
    assert measured.denominator == pytest.approx(50.0)
    assert measured.value == pytest.approx(1.0)


def test_ratio_of_legs_rejects_zero_denominator() -> None:
    with pytest.raises(ValueError, match="zero-length"):
        ratio_of_legs(
            name="bad",
            numerator_start=1.0,
            numerator_end=2.0,
            denominator_start=3.0,
            denominator_end=3.0,
        )


@pytest.mark.parametrize(
    ("c_retracement", "targets"),
    [
        (0.382, (2.24, 2.618)),
        (0.500, (2.0,)),
        (0.618, (1.618,)),
        (0.707, (1.414,)),
        (0.786, (1.272,)),
        (0.886, (1.13,)),
    ],
)
def test_abcd_reciprocal_table(c_retracement: float, targets: tuple[float, ...]) -> None:
    assert reciprocal_bc_targets(c_retracement) == targets


def test_reciprocal_lookup_does_not_silently_round_far_values() -> None:
    assert reciprocal_bc_targets(0.73) == ()
