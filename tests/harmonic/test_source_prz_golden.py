import pytest

from htcn.harmonic.models import HarmonicPoint, PatternDirection
from htcn.harmonic.prz import PRZComponent, build_xabcd_prz
from htcn.harmonic.rules import CARNEY_RULES
from htcn.harmonic.source_prz import SOURCE_PRZ_PROFILES, select_source_prz


_SOURCE_CASES = {
    # Normalized XABC structures derived from the source specification tables.  They are
    # executable specification fixtures, not claims that every textbook market chart has
    # these normalized prices.
    "gartley": {
        "b": 0.618,
        "c": 0.707,
        "bc": "BC projection x1.414",
        "abcd": "AB=CD x1",
        "method": "compact_three_measure",
    },
    "bat": {
        "b": 0.50,
        "c": 0.618,
        "bc": "BC projection x2.24",
        "abcd": "AB=CD x1.27",
        "method": "compact_three_measure",
    },
    "butterfly": {
        "b": 0.786,
        "c": 0.618,
        "bc": "BC projection x2",
        "abcd": "AB=CD x1.27",
        "method": "compact_three_measure",
    },
    "crab": {
        "b": 0.50,
        "c": 0.618,
        "bc": "BC projection x3.618",
        "abcd": "AB=CD x1.618",
        "method": "xa_bc_primary",
    },
    "deep_crab": {
        "b": 0.886,
        "c": 0.618,
        "bc": "BC projection x2.618",
        "abcd": "AB=CD x1.618",
        "method": "compact_three_measure",
    },
}


def _normalized_xabc(
    pattern_id: str,
    direction: PatternDirection,
) -> tuple[HarmonicPoint, HarmonicPoint, HarmonicPoint, HarmonicPoint]:
    spec = _SOURCE_CASES[pattern_id]
    b_ratio = float(spec["b"])
    c_ratio = float(spec["c"])

    if direction is PatternDirection.BULLISH:
        x_price, a_price = 100.0, 200.0
        b_price = a_price - b_ratio * (a_price - x_price)
        c_price = b_price + c_ratio * (a_price - b_price)
    else:
        x_price, a_price = 200.0, 100.0
        b_price = a_price + b_ratio * (x_price - a_price)
        c_price = b_price - c_ratio * (b_price - a_price)

    return (
        HarmonicPoint("X", 0, x_price),
        HarmonicPoint("A", 10, a_price),
        HarmonicPoint("B", 20, b_price),
        HarmonicPoint("C", 30, c_price),
    )


@pytest.mark.parametrize("pattern_id", tuple(_SOURCE_CASES))
@pytest.mark.parametrize("direction", (PatternDirection.BULLISH, PatternDirection.BEARISH))
def test_source_prz_golden_profiles_freeze_auditable_three_measure_zone(
    pattern_id: str,
    direction: PatternDirection,
) -> None:
    spec = _SOURCE_CASES[pattern_id]
    prz = build_xabcd_prz(CARNEY_RULES[pattern_id], _normalized_xabc(pattern_id, direction))

    assert prz.direction is direction
    assert prz.has_source_prz is True
    assert prz.source_prz_status == "frozen"
    assert prz.source_prz_defining_component == "XA completion"
    assert prz.source_prz_selection_method == spec["method"]
    assert prz.source_prz_component_names == (
        "XA completion",
        spec["bc"],
        spec["abcd"],
    )
    assert prz.source_prz_source_refs
    assert prz.source_prz_note
    assert prz.source_prz_reason is None

    selected = [component for component in prz.components if component.name in prz.source_prz_component_names]
    assert len(selected) == 3
    assert prz.source_prz_low == pytest.approx(min(component.price_low for component in selected))
    assert prz.source_prz_high == pytest.approx(max(component.price_high for component in selected))

    # Raw PRZ is a source-selected subset of the audit collection.  It may numerically
    # coincide with the HT-CN ideal core in a clean case, but it must never become the
    # all-components envelope merely because more variants are stored for audit.
    assert prz.component_envelope_low <= prz.source_prz_low <= prz.source_prz_high <= prz.component_envelope_high
    assert len(prz.components) > len(prz.source_prz_component_names)


def test_profile_registry_freezes_only_source_cleared_standard_xabcd() -> None:
    for pattern_id in ("gartley", "bat", "butterfly", "crab", "deep_crab"):
        assert SOURCE_PRZ_PROFILES[pattern_id].status == "frozen"
    assert SOURCE_PRZ_PROFILES["alternate_bat"].status == "source_conflict"


def test_alternate_bat_source_conflict_remains_fail_closed() -> None:
    points = (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 10, 200.0),
        HarmonicPoint("B", 20, 170.0),
        HarmonicPoint("C", 30, 188.54),
    )
    prz = build_xabcd_prz(CARNEY_RULES["alternate_bat"], points)
    assert prz.has_source_prz is False
    assert prz.source_prz_low is None
    assert prz.source_prz_high is None
    assert prz.source_prz_status == "source_conflict_fail_closed"
    assert prz.source_prz_reason == "source_conflict"
    assert prz.source_prz_component_names == ()
    assert "Volume Two" in " ".join(prz.source_prz_source_refs)
    assert "Volume Three" in " ".join(prz.source_prz_source_refs)


def test_source_selector_never_falls_back_to_ideal_core_when_required_members_are_missing() -> None:
    components = (
        PRZComponent(
            name="XA completion",
            price_low=100.0,
            price_high=100.0,
            ratio_low=0.886,
            ratio_high=0.886,
        ),
    )
    selection = select_source_prz("bat", components)
    assert selection.available is False
    assert selection.price_low is None
    assert selection.price_high is None
    assert selection.reason == "required_components_missing:bc+abcd"
