import pandas as pd
import pytest

from htcn.harmonic.pine_r34 import (
    PINE_R34_SOURCE_SHA256,
    PineR34Pivot,
    _candidate_rank,
    _candidate_visible,
    _geometry,
    _observable,
    _strict_pivot,
    pine_atr,
    scan_pine_r34,
)


def _nodes(prices, kinds):
    return tuple(
        PineR34Pivot(index=i * 10, price=float(price), kind=kind, scale=5, confirmed_at=i * 10 + 5)
        for i, (price, kind) in enumerate(zip(prices, kinds, strict=True))
    )


@pytest.mark.parametrize(
    ("rule", "prices", "kinds", "pattern"),
    [
        (0, [100, 200, 138.2, 183.2], [-1, 1, -1, 1], "gartley"),
        (1, [100, 200, 150, 180], [-1, 1, -1, 1], "bat"),
        (2, [100, 200, 161.8, 190], [-1, 1, -1, 1], "alternate_bat"),
        (3, [100, 200, 121.4, 170], [-1, 1, -1, 1], "butterfly"),
        (4, [100, 200, 150, 192.8], [-1, 1, -1, 1], "crab"),
        (5, [100, 200, 111.4, 181.5], [-1, 1, -1, 1], "deep_crab"),
        (6, [100, 200, 150, 210], [-1, 1, -1, 1], "shark"),
        (7, [200, 100, 150, 80, 200], [1, -1, 1, -1, 1], "five_zero"),
        (8, [180, 100, 150], [1, -1, 1], "abcd"),
        (9, [180, 100, 150], [1, -1, 1], "abcd_127"),
        (10, [180, 100, 150], [1, -1, 1], "abcd_1618"),
        (11, [100, 200, 138.2, 173.2], [-1, 1, -1, 1], "deep_gartley"),
    ],
)
def test_r34_family_geometry_projects_a_valid_completion_zone(rule, prices, kinds, pattern):
    result = _geometry(
        rule,
        _nodes(prices, kinds),
        atr=10.0,
        tick=0.01,
        min_leg_atr=0.35,
        max_bars=500,
        cluster_width=0.12,
        abcd_tolerance_pct=3.0,
        abcd_convergence_pct=3.0,
    )

    assert result.ok, (pattern, result)
    assert result.low is not None and result.high is not None
    assert result.low > 0
    assert result.high >= result.low
    assert result.limit is not None
    assert (result.low > result.limit) if result.direction == 1 else (result.high < result.limit)


def test_r34_equal_abcd_precise_gate_matches_three_percent_pairing():
    result = _geometry(
        8,
        _nodes([180, 100, 150], [1, -1, 1]),
        atr=10.0,
        tick=0.01,
        min_leg_atr=0.35,
        max_bars=500,
        cluster_width=0.12,
        abcd_tolerance_pct=3.0,
        abcd_convergence_pct=3.0,
    )
    assert result.ok
    assert result.qualified
    assert result.precise
    assert result.c_ideal == pytest.approx(0.618)
    assert result.bc_ideal == pytest.approx(1.618)


def test_r34_alt_bat_five_zero_extended_abcd_and_deep_gartley_are_research_only():
    # Full scanner boundary is asserted through the helper classification indirectly by
    # deterministic rule policy: these families cannot become canonical HT-CN identity.
    from htcn.harmonic.pine_r34 import _research_only

    for rule in (2, 7, 9, 10, 11):
        assert _research_only(rule, True, True)
    assert not _research_only(0, True, True)
    assert not _research_only(6, True, True)


def test_r34_pivot_is_only_knowable_after_right_confirmation():
    frame = pd.DataFrame(
        {
            "open": [10, 11, 12, 14, 12, 11, 10],
            "high": [11, 12, 13, 15, 13, 12, 11],
            "low": [9, 10, 11, 13, 11, 10, 9],
            "close": [10, 11, 12, 14, 12, 11, 10],
        }
    )
    highs = frame["high"].astype(float).tolist()
    lows = frame["low"].astype(float).tolist()

    assert _strict_pivot(highs, lows, confirmation_bar=4, strength=2, scale=2) is None
    pivot = _strict_pivot(highs, lows, confirmation_bar=5, strength=2, scale=2)
    assert pivot is not None
    assert pivot.index == 3
    assert pivot.confirmed_at == 5
    assert pivot.kind == 1


def test_r34_tied_extreme_is_fail_closed():
    highs = [10.0, 12.0, 15.0, 15.0, 12.0, 10.0]
    lows = [8.0, 9.0, 10.0, 10.0, 9.0, 8.0]
    assert _strict_pivot(highs, lows, confirmation_bar=4, strength=2, scale=2) is None
    assert _strict_pivot(highs, lows, confirmation_bar=5, strength=2, scale=2) is None


def test_pine_atr_uses_wilder_rma_seed():
    frame = pd.DataFrame(
        {
            "open": [10, 10, 10, 10],
            "high": [12, 13, 14, 15],
            "low": [9, 9, 10, 11],
            "close": [11, 12, 13, 14],
        }
    )
    values = pine_atr(frame, length=3)
    # TR = 3, 4, 4, 4. Seed at bar 2 = 11/3, then Wilder alpha=1/3.
    assert values[:2] == (None, None)
    assert values[2] == pytest.approx(11 / 3)
    assert values[3] == pytest.approx((11 / 3) * (2 / 3) + 4 * (1 / 3))


def test_r34_scan_declares_retained_source_identity():
    empty = pd.DataFrame(columns=["open", "high", "low", "close"])
    scan = scan_pine_r34(empty)
    assert scan.candidates == ()
    assert PINE_R34_SOURCE_SHA256 == "84e1eb2267c9b80891e0ffb64a6d4abf5712fc5e756be81815e536f2fca4c3f5"



@pytest.mark.parametrize(
    ("price", "low", "high", "atr", "expected"),
    [
        (101.0, 100.0, 102.0, 2.0, True),
        (105.0, 100.0, 102.0, 2.0, True),
        (110.0, 100.0, 102.0, 2.0, False),
        (101.0, 95.0, 105.0, 2.0, False),
    ],
)
def test_r34_observable_matches_near_journey_and_width_filters(
    price,
    low,
    high,
    atr,
    expected,
):
    assert _observable(price, low, high, atr) is expected


def test_r34_candidate_rank_preserves_pine_priority_terms():
    standard = _candidate_rank(
        near_enough=True,
        active_event=False,
        rule=0,
        source_age=10,
        distance_atr=0.5,
    )
    abcd = _candidate_rank(
        near_enough=True,
        active_event=False,
        rule=8,
        source_age=10,
        distance_atr=0.5,
    )
    active = _candidate_rank(
        near_enough=True,
        active_event=True,
        rule=0,
        source_age=10,
        distance_atr=0.5,
    )

    assert standard - abcd == pytest.approx(20.0)
    assert active - standard == pytest.approx(100000.0)


def test_r34_candidate_visibility_hides_old_remote_structure_by_default():
    assert _candidate_visible(
        live=True,
        near_enough=False,
        developing=True,
        age=180,
        max_age=180,
        research=False,
    )
    assert not _candidate_visible(
        live=True,
        near_enough=False,
        developing=True,
        age=181,
        max_age=180,
        research=False,
    )
    assert _candidate_visible(
        live=True,
        near_enough=False,
        developing=False,
        age=500,
        max_age=180,
        research=True,
    )
    assert not _candidate_visible(
        live=False,
        near_enough=True,
        developing=True,
        age=1,
        max_age=180,
        research=True,
    )
