from itertools import pairwise

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


def test_r34_pivot_plateau_keeps_latest_equal_high_like_pine():
    highs = [10.0, 12.0, 15.0, 15.0, 12.0, 10.0]
    lows = [8.0, 9.0, 10.0, 10.0, 9.0, 8.0]

    # The earlier equal high is invalid because an equal value still exists on its
    # newer/right side.
    assert _strict_pivot(
        highs,
        lows,
        confirmation_bar=4,
        strength=2,
        scale=2,
    ) is None

    # The later equal high is retained: the equal plateau value is only on its
    # older/left side, matching Pine's last-occurrence pivot tie-break.
    pivot = _strict_pivot(
        highs,
        lows,
        confirmation_bar=5,
        strength=2,
        scale=2,
    )
    assert pivot is not None
    assert pivot.index == 3
    assert pivot.price == 15.0
    assert pivot.kind == 1


def test_r34_pivot_plateau_keeps_latest_equal_low_like_pine():
    highs = [12.0, 11.0, 10.0, 10.0, 11.0, 12.0]
    lows = [9.0, 8.0, 5.0, 5.0, 8.0, 9.0]

    assert _strict_pivot(
        highs,
        lows,
        confirmation_bar=4,
        strength=2,
        scale=2,
    ) is None

    pivot = _strict_pivot(
        highs,
        lows,
        confirmation_bar=5,
        strength=2,
        scale=2,
    )
    assert pivot is not None
    assert pivot.index == 3
    assert pivot.price == 5.0
    assert pivot.kind == -1


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



def _piecewise_frame(
    anchors: list[tuple[int, float]],
    *,
    rows: int,
    wick: float = 0.25,
    overrides: dict[int, dict[str, float]] | None = None,
) -> pd.DataFrame:
    closes: list[float] = [0.0] * rows
    for segment, ((left_i, left_p), (right_i, right_p)) in enumerate(
        pairwise(anchors)
    ):
        span = right_i - left_i
        assert span > 0, segment
        for index in range(left_i, right_i + 1):
            fraction = (index - left_i) / span
            closes[index] = left_p + (right_p - left_p) * fraction
    first_i, first_p = anchors[0]
    for index in range(first_i):
        closes[index] = first_p + (first_i - index) * 0.05
    last_i, last_p = anchors[-1]
    for index in range(last_i, rows):
        closes[index] = last_p - (index - last_i) * 0.05

    rows_out: list[dict[str, float]] = []
    overrides = overrides or {}
    for index, close in enumerate(closes):
        row = {
            "open": close,
            "high": close + wick,
            "low": close - wick,
            "close": close,
            "volume": 1000.0,
        }
        row.update(overrides.get(index, {}))
        rows_out.append(row)
    return pd.DataFrame(rows_out)


def test_r34_full_scan_gartley_locks_nodes_birth_and_projected_prz():
    frame = _piecewise_frame(
        [(5, 100.0), (15, 200.0), (25, 138.2), (35, 183.2), (55, 160.0)],
        rows=60,
        wick=0.0,
    )

    scan = scan_pine_r34(frame, scales=(2,))
    candidate = next(
        item
        for item in scan.candidates
        if item.pattern_id == "gartley"
        and item.conflict_key == (5, 15, 25, 35)
    )

    assert [node.kind for node in candidate.source_nodes] == [-1, 1, -1, 1]
    assert [node.confirmed_at for node in candidate.source_nodes] == [7, 17, 27, 37]
    # Pine pivots are built from low/high, not close. The synthetic fixture has
    # a 0.25 wick, so lock the actual pivot prices used by R3.4.
    assert [node.price for node in candidate.source_nodes] == pytest.approx(
        [99.75, 200.25, 137.95, 183.45]
    )
    assert candidate.born_bar == 37
    assert candidate.m1 == pytest.approx(121.26)
    assert candidate.m2 == pytest.approx(121.15)
    assert candidate.m3 == pytest.approx(119.11)
    assert candidate.prz_low == pytest.approx(119.11)
    assert candidate.prz_high == pytest.approx(121.26)
    assert candidate.structural_limit == pytest.approx(99.75)
    assert candidate.live


def test_r34_full_scan_never_backfills_prz_touch_before_c_confirmation():
    frame = _piecewise_frame(
        [(5, 100.0), (15, 200.0), (25, 138.2), (35, 183.2), (55, 160.0)],
        rows=60,
        wick=0.0,
        overrides={
            # C is not knowable until bar 37. This pre-confirmation bar touches the
            # projected Gartley PRZ but must never be donated to the future structure.
            36: {
                "open": 180.0,
                "high": 182.0,
                "low": 120.0,
                "close": 180.0,
            },
        },
    )

    scan = scan_pine_r34(frame, scales=(2,))
    candidate = next(
        item
        for item in scan.candidates
        if item.pattern_id == "gartley"
        and item.conflict_key == (5, 15, 25, 35)
    )

    assert candidate.born_bar == 37
    assert candidate.first_test_bar is None
    assert candidate.test_count == 0


def test_r34_full_scan_first_post_birth_complete_prz_test_is_timestamped():
    frame = _piecewise_frame(
        [(5, 100.0), (15, 200.0), (25, 138.2), (35, 183.2), (55, 160.0)],
        rows=60,
        overrides={
            38: {
                "open": 123.0,
                "high": 123.5,
                "low": 119.0,
                "close": 122.0,
            },
        },
    )

    scan = scan_pine_r34(frame, scales=(2,))
    candidate = next(
        item
        for item in scan.candidates
        if item.pattern_id == "gartley"
        and item.conflict_key == (5, 15, 25, 35)
    )

    assert candidate.born_bar == 37
    assert candidate.first_test_bar == 38
    assert candidate.test_count == 1



@pytest.mark.parametrize(
    ("pattern_id", "anchors", "expected_nodes", "expected_schema", "research_only"),
    [
        (
            "abcd",
            [(0, 150.0), (5, 180.0), (15, 100.0), (25, 150.0), (45, 120.0)],
            (5, 15, 25),
            "ABCD",
            False,
        ),
        (
            "shark",
            [(5, 100.0), (15, 200.0), (25, 150.0), (35, 210.0), (55, 180.0)],
            (5, 15, 25, 35),
            "0XABC",
            False,
        ),
        (
            "five_zero",
            [(0, 150.0), (5, 200.0), (15, 100.0), (25, 150.0), (35, 80.0), (45, 200.0), (65, 170.0)],
            (5, 15, 25, 35, 45),
            "0XABCD",
            True,
        ),
    ],
)
def test_r34_full_scan_supports_all_source_topologies(
    pattern_id,
    anchors,
    expected_nodes,
    expected_schema,
    research_only,
):
    frame = _piecewise_frame(
        anchors,
        rows=anchors[-1][0] + 8,
        wick=0.0,
    )
    scan = scan_pine_r34(frame, scales=(2,))

    candidate = next(
        item
        for item in scan.candidates
        if item.pattern_id == pattern_id
        and item.conflict_key == expected_nodes
    )

    assert candidate.schema == expected_schema
    assert candidate.born_bar == expected_nodes[-1] + 2
    assert candidate.research_only is research_only
    assert candidate.prz_low > candidate.structural_limit
    assert candidate.prz_high >= candidate.prz_low


def test_r34_precise_abcd_full_scan_keeps_two_measurement_convergence():
    frame = _piecewise_frame(
        [(0, 150.0), (5, 180.0), (15, 100.0), (25, 150.0), (45, 120.0)],
        rows=53,
        wick=0.0,
    )
    scan = scan_pine_r34(frame, scales=(2,))
    candidate = next(
        item
        for item in scan.candidates
        if item.pattern_id == "abcd"
        and item.conflict_key == (5, 15, 25)
    )

    assert candidate.precise
    assert candidate.qualified
    assert not candidate.research_only
    assert [node.price for node in candidate.source_nodes] == pytest.approx(
        [180.25, 99.75, 150.25]
    )
    assert candidate.m1 == pytest.approx(69.75)
    assert candidate.m2 == pytest.approx(68.54)
    assert candidate.prz_low == pytest.approx(68.54)
    assert candidate.prz_high == pytest.approx(69.75)



def test_r34_retains_confirmed_pivots_before_atr_seed_is_ready():
    frame = _piecewise_frame(
        [(5, 100.0), (15, 200.0), (25, 138.2), (35, 183.2), (55, 160.0)],
        rows=60,
    )

    scan = scan_pine_r34(frame, scales=(2,), atr_length=14)
    pivots = scan.pivots_by_scale[2]

    assert any(
        pivot.index == 5 and pivot.confirmed_at == 7 and pivot.kind == -1
        for pivot in pivots
    )
    assert any(
        item.pattern_id == "gartley"
        and item.conflict_key == (5, 15, 25, 35)
        for item in scan.candidates
    )
