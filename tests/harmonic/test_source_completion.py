from itertools import pairwise

import pandas as pd

from htcn.harmonic.source_completion import (
    event_sourced_hierarchical_xabc_projections,
    scan_source_completion_events,
)


def _gartley_path(*, terminal: bool) -> pd.DataFrame:
    anchors = [
        (0, 120.0),
        (10, 100.0),
        (30, 200.0),
        (50, 138.2),
        (70, 183.2),
    ]
    if terminal:
        anchors.extend(
            [
                (90, 121.0),
                (110, 145.0),
            ]
        )
        rows = 111
    else:
        anchors.extend(
            [
                (90, 165.0),
                (110, 170.0),
            ]
        )
        rows = 111

    closes = [0.0] * rows
    for (left_i, left_p), (right_i, right_p) in pairwise(anchors):
        for index in range(left_i, right_i + 1):
            fraction = (index - left_i) / (right_i - left_i)
            closes[index] = left_p + (right_p - left_p) * fraction
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * rows,
        }
    )


def test_event_sourced_projection_birth_precedes_future_terminal() -> None:
    frame = _gartley_path(terminal=True)

    projections = event_sourced_hierarchical_xabc_projections(
        frame,
        scales=(3,),
    )
    gartley = [item for item in projections if item.pattern_id == "gartley"]

    assert gartley
    assert gartley[0].node_indices == (10, 30, 50, 70)
    assert gartley[0].known_at >= 73

    scan = scan_source_completion_events(frame, scales=(3,))
    completions = [
        item
        for item in scan.completions
        if item.pattern_id == "gartley"
        and item.source_nodes == (10, 30, 50, 70)
    ]

    assert completions
    assert completions[0].terminal_bar > completions[0].known_at
    assert completions[0].audit.first_prz_entry_bar is not None


def test_projection_does_not_become_completed_without_future_terminal_test() -> None:
    frame = _gartley_path(terminal=False)

    projections = event_sourced_hierarchical_xabc_projections(
        frame,
        scales=(3,),
    )
    assert any(item.pattern_id == "gartley" for item in projections)

    scan = scan_source_completion_events(frame, scales=(3,))
    assert not any(
        item.pattern_id == "gartley"
        and item.source_nodes == (10, 30, 50, 70)
        for item in scan.completions
    )
