import pytest

from htcn.harmonic.five_zero import evaluate_five_zero, project_forming_five_zero
from htcn.harmonic.models import HarmonicPoint, PatternDirection, PatternState


def _points(values):
    return tuple(
        HarmonicPoint(label=label, index=index, price=price)
        for index, (label, price) in enumerate(values)
    )


def test_bullish_five_zero_volume2_raw_prz_uses_only_50_bc_and_reciprocal():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 150.0), ("D", 120.0)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BULLISH
    assert result.metrics.b_xa.value == pytest.approx(1.5)
    assert result.metrics.c_ab.value == pytest.approx(2.0)
    assert result.metrics.d_bc.value == pytest.approx(0.5)
    assert result.metrics.cd_ab.value == pytest.approx(1.0)
    assert result.completion_class == "source_raw_prz_test"
    assert result.source_raw_prz_test is True

    prz = result.prz
    assert prz.has_source_prz is True
    assert prz.source_prz_component_names == (
        "BC 50% structural completion",
        "Reciprocal AB=CD x1",
    )
    assert "BC 61.8% V3 execution boundary" not in prz.source_prz_component_names
    assert prz.source_prz_defining_component == "BC 50% structural completion"
    assert prz.source_prz_selection_method == "volume2_50_bc_plus_reciprocal_abcd"

    refinement = result.source_contract.execution_refinement
    assert refinement.raw_prz_membership is False
    assert refinement.identity_membership is False
    assert refinement.source_label_status == "conflicted_xa_ab_labels_vs_bc_axis_figures"


def test_bearish_five_zero_source_geometry_is_symmetric():
    points = _points((("X", 120.0), ("A", 100.0), ("B", 130.0), ("C", 70.0), ("D", 100.0)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.COMPLETED
    assert result.direction is PatternDirection.BEARISH
    assert result.completion_class == "source_raw_prz_test"
    assert result.prz.source_prz_low == pytest.approx(100.0)
    assert result.prz.source_prz_high == pytest.approx(100.0)


def test_reciprocal_before_50_is_source_valid_and_not_rejected_by_legacy_band():
    # AB=30, BC=66 => C/AB=2.20.  On the bullish decline from C, the reciprocal
    # completion at 126 is encountered before the 50% BC level at 123.  Volume Three
    # explicitly permits immediate execution at that reciprocal level.
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 156.0), ("D", 126.0)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.COMPLETED
    assert result.metrics.c_ab.value == pytest.approx(2.2)
    assert result.metrics.d_bc.value < 0.50
    assert result.source_contract.reciprocal_relation == "before_50"
    assert result.source_contract.price_50_bc == pytest.approx(123.0)
    assert result.reciprocal_abcd_price == pytest.approx(126.0)
    assert result.reciprocal_inside_execution_band is False  # deprecated diagnostic only
    assert result.completion_class == "source_raw_prz_test"
    assert result.source_raw_prz_test is True
    assert result.source_contract.execution_refinement.preferred_execution_price == pytest.approx(126.0)
    assert result.reasons == ()


def test_reciprocal_beyond_50_can_use_v3_618_execution_refinement_without_expanding_raw_prz():
    # AB=30, BC=54 => C/AB=1.80.  Reciprocal=114 lies beyond the 50% level=117;
    # V3 then treats the 61.8 level=110.628 as the optimal execution refinement.
    d_618 = 144.0 - 0.618 * 54.0
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 144.0), ("D", d_618)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.COMPLETED
    assert result.source_contract.reciprocal_relation == "beyond_50_toward_618"
    assert result.source_contract.price_50_bc == pytest.approx(117.0)
    assert result.reciprocal_abcd_price == pytest.approx(114.0)
    assert result.prz.source_prz_low == pytest.approx(114.0)
    assert result.prz.source_prz_high == pytest.approx(117.0)
    assert result.prz.source_prz_component_names == (
        "BC 50% structural completion",
        "Reciprocal AB=CD x1",
    )
    assert result.source_raw_prz_test is False
    assert result.within_v3_execution_envelope is True
    assert result.completion_class == "v3_618_execution_refinement"
    assert result.source_contract.execution_refinement.price_618 == pytest.approx(d_618)
    assert result.source_contract.execution_refinement.preferred_execution_price == pytest.approx(d_618)


def test_five_zero_rejects_completion_beyond_v3_618_boundary():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 144.0), ("D", 109.0)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.REJECTED
    assert result.completion_class == "outside_reconciled_completion_zone"
    assert any("reconciled Volume Three" in reason for reason in result.reasons)


def test_five_zero_rejects_c_leg_below_mandatory_1618():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 135.0), ("D", 112.5)))
    result = evaluate_five_zero(points)

    assert result.state is PatternState.REJECTED
    assert any("C/AB" in reason for reason in result.reasons)


def test_forming_five_zero_keeps_reciprocal_before_50_candidate():
    points = _points((("X", 100.0), ("A", 120.0), ("B", 90.0), ("C", 156.0)))
    projection = project_forming_five_zero(points)

    assert projection is not None
    assert projection.direction is PatternDirection.BULLISH
    assert projection.reciprocal_abcd_price == pytest.approx(126.0)
    assert projection.source_contract.price_50_bc == pytest.approx(123.0)
    assert projection.source_contract.reciprocal_relation == "before_50"
    assert projection.prz.source_prz_low == pytest.approx(123.0)
    assert projection.prz.source_prz_high == pytest.approx(126.0)
    assert projection.source_contract.legacy_reciprocal_inside_50_618_band is False
