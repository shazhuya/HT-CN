import pandas as pd

from htcn.harmonic.discovery import (
    discover_pivots,
    iter_discovery_xabc_windows,
    iter_hierarchical_xabcd_windows,
)
from htcn.harmonic.models import Pivot, PivotKind


def _pivot(index: int, price: float, kind: PivotKind, scale: int = 5) -> Pivot:
    return Pivot(
        index=index,
        price=price,
        kind=kind,
        scale=scale,
        confirmed_at=index + scale,
    )


def _frame(rows: int = 70, *, preconfirm_touch: bool = False, postconfirm_touch: bool = False) -> pd.DataFrame:
    data = []
    for index in range(rows):
        low = 125.0
        high = 130.0
        if preconfirm_touch and index == 34:
            low, high = 103.5, 105.0
        if postconfirm_touch and index == 36:
            low, high = 103.5, 105.0
        data.append(
            {
                "open": 128.0,
                "high": high,
                "low": low,
                "close": 128.0,
                "volume": 1000.0,
            }
        )
    return pd.DataFrame(data)


def _gartley_xabc(*, c_price: float = 116.64) -> list[Pivot]:
    return [
        _pivot(0, 100.0, PivotKind.LOW),
        _pivot(10, 120.0, PivotKind.HIGH),
        _pivot(20, 107.64, PivotKind.LOW),
        _pivot(30, c_price, PivotKind.HIGH),
    ]


def test_discovery_retains_historical_xabc_after_later_confirmed_pivots() -> None:
    pivots = [
        *_gartley_xabc(),
        _pivot(40, 105.0, PivotKind.LOW),
        _pivot(50, 114.0, PivotKind.HIGH),
    ]

    windows = iter_discovery_xabc_windows(pivots)
    node_sets = {
        tuple(pivot.index for pivot in item.window.pivots)
        for item in windows
    }

    assert (0, 10, 20, 30) in node_sets
    assert (20, 30, 40, 50) in node_sets


def test_discovery_keeps_source_band_candidate_outside_three_percent_c_family_gate() -> None:
    # C/AB = 0.75 is inside the source structural 0.382-0.886 envelope but is not within
    # the authoritative engine's 3% operational matching radius of the discrete C family.
    pivots = _gartley_xabc(c_price=116.91)
    scan = discover_pivots({5: pivots}, _frame())

    gartley = next(
        candidate
        for candidate in scan.candidates
        if candidate.pattern_id == "gartley"
        and candidate.conflict_key == (0, 10, 20, 30)
    )

    assert abs(gartley.c_ab - 0.75) < 1e-12
    assert gartley.source_family_aligned is False
    assert gartley.c_family_relative_error is not None
    assert gartley.c_family_relative_error > 0.03
    assert gartley.prz.has_source_prz
    assert gartley.prz_status == "projected"


def test_discovery_can_skip_one_complete_minor_swing_pair() -> None:
    pivots = [
        _pivot(0, 100.0, PivotKind.LOW),
        _pivot(10, 120.0, PivotKind.HIGH),
        _pivot(13, 112.0, PivotKind.LOW),
        _pivot(16, 117.0, PivotKind.HIGH),
        _pivot(20, 107.64, PivotKind.LOW),
        _pivot(30, 116.64, PivotKind.HIGH),
    ]

    scan = discover_pivots({5: pivots}, _frame())
    gartley = next(
        candidate
        for candidate in scan.candidates
        if candidate.pattern_id == "gartley"
        and candidate.conflict_key == (0, 10, 20, 30)
    )

    assert gartley.path_kind == "minor_swing_skip"
    assert gartley.skipped_pivots == 2
    assert tuple(point.index for point in gartley.points) == (0, 10, 20, 30)


def test_discovery_prz_test_clock_starts_at_c_confirmation_without_backfill() -> None:
    pivots = _gartley_xabc()
    pre = discover_pivots(
        {5: pivots},
        _frame(preconfirm_touch=True),
    )
    pre_candidate = next(
        candidate
        for candidate in pre.candidates
        if candidate.pattern_id == "gartley"
        and candidate.conflict_key == (0, 10, 20, 30)
    )

    assert pre_candidate.known_from_bar == 35
    assert pre_candidate.first_prz_test_bar is None
    assert pre_candidate.prz_status == "projected"

    post = discover_pivots(
        {5: pivots},
        _frame(preconfirm_touch=True, postconfirm_touch=True),
    )
    post_candidate = next(
        candidate
        for candidate in post.candidates
        if candidate.pattern_id == "gartley"
        and candidate.conflict_key == (0, 10, 20, 30)
    )

    assert post_candidate.first_prz_test_bar == 36
    assert post_candidate.prz_status == "tested"


def test_discovery_dedupes_identical_geometry_across_scales() -> None:
    scale5 = _gartley_xabc()
    scale10 = [
        Pivot(
            index=pivot.index,
            price=pivot.price,
            kind=pivot.kind,
            scale=10,
            confirmed_at=pivot.index + 10,
        )
        for pivot in scale5
    ]
    scan = discover_pivots({5: scale5, 10: scale10}, _frame())

    gartleys = [
        candidate
        for candidate in scan.candidates
        if candidate.pattern_id == "gartley"
        and candidate.conflict_key == (0, 10, 20, 30)
    ]
    assert len(gartleys) == 1


def test_hierarchical_graph_can_span_two_minor_swing_pairs_when_endpoints_dominate() -> None:
    pivots = [
        _pivot(0, 100.0, PivotKind.LOW),
        _pivot(2, 108.0, PivotKind.HIGH),
        _pivot(4, 103.0, PivotKind.LOW),
        _pivot(6, 112.0, PivotKind.HIGH),
        _pivot(8, 106.0, PivotKind.LOW),
        _pivot(10, 120.0, PivotKind.HIGH),
        _pivot(12, 114.0, PivotKind.LOW),
        _pivot(14, 118.0, PivotKind.HIGH),
        _pivot(16, 111.0, PivotKind.LOW),
        _pivot(18, 116.0, PivotKind.HIGH),
        _pivot(20, 107.64, PivotKind.LOW),
        _pivot(30, 116.64, PivotKind.HIGH),
        _pivot(40, 104.28, PivotKind.LOW),
    ]

    windows = iter_hierarchical_xabcd_windows(
        pivots,
        recent_pivots=20,
        max_leg_step=7,
        max_total_skips=12,
    )
    nodes = {
        tuple(pivot.index for pivot in item.window.pivots)
        for item in windows
    }

    assert (0, 10, 20, 30, 40) in nodes


def test_hierarchical_graph_rejects_skip_when_interior_same_kind_breaks_dominance() -> None:
    pivots = [
        _pivot(0, 100.0, PivotKind.LOW),
        _pivot(2, 108.0, PivotKind.HIGH),
        _pivot(4, 99.0, PivotKind.LOW),
        _pivot(6, 112.0, PivotKind.HIGH),
        _pivot(8, 106.0, PivotKind.LOW),
        _pivot(10, 120.0, PivotKind.HIGH),
        _pivot(20, 107.64, PivotKind.LOW),
        _pivot(30, 116.64, PivotKind.HIGH),
        _pivot(40, 104.28, PivotKind.LOW),
    ]

    windows = iter_hierarchical_xabcd_windows(
        pivots,
        recent_pivots=20,
        max_leg_step=7,
        max_total_skips=12,
    )
    nodes = {
        tuple(pivot.index for pivot in item.window.pivots)
        for item in windows
    }

    assert (0, 10, 20, 30, 40) not in nodes
