import json
from dataclasses import replace
from itertools import pairwise
from pathlib import Path

import pandas as pd

from htcn.harmonic.source_completion import (
    _recognition_source_execution,
    event_sourced_hierarchical_xabc_projections,
    scan_source_completion_events,
)


def test_birth_evidence_is_not_backfilled_by_later_scales() -> None:
    frame = _gartley_path(terminal=True)
    def target(data):
        return next(p for p in event_sourced_hierarchical_xabc_projections(data)
                    if p.pattern_id == "gartley" and p.node_indices == (10, 30, 50, 70))
    early, late = target(frame.iloc[:75]), target(frame)
    assert (early.known_at, early.scales, early.min_skipped_pivots) == (
        late.known_at, late.scales, late.min_skipped_pivots
    )
    assert late.scales_as_of(72) == ()
    assert late.scales_as_of(74) == (3,)
    assert late.scales_as_of(78) == (3, 5, 8)


def test_gap_return_cannot_complete_old_projection_in_either_direction() -> None:
    for bearish in (False, True):
        frame = _gartley_path(terminal=True).iloc[:86].copy()
        frame.loc[80, ["open", "high", "low", "close"]] = [90, 95, 85, 90]
        frame.loc[81, ["open", "high", "low", "close"]] = [120, 125, 115, 120]
        if bearish:
            high, low = frame["high"].copy(), frame["low"].copy()
            frame["high"], frame["low"] = 400 - low, 400 - high
            frame["open"], frame["close"] = 400 - frame["open"], 400 - frame["close"]
        scan = scan_source_completion_events(frame, scales=(3,))
        state = next(s for s in scan.states if s.projection.pattern_id == "gartley"
                     and s.projection.node_indices == (10, 30, 50, 70))
        assert state.state == "invalidated"
        assert state.closed_bar == 80
        assert state.reason == "unobserved_far_side_passage_retired_policy_v2"


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
                (90, 119.0),
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
    frame = pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * rows,
        }
    )
    if terminal:
        # Source Terminal requires actual PRZ contact. A bar wholly below the zone is gap-through.
        # Cover all PRZ measurements, not only its far boundary.
        frame.loc[90, "high"] = 123.0
    return frame


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


def test_c_extreme_breach_invalidates_and_later_prz_touch_cannot_resurrect() -> None:
    frame = _gartley_path(terminal=True)
    frame.loc[75, "high"] = 185.0

    scan = scan_source_completion_events(frame, scales=(3,))
    target_states = [
        item
        for item in scan.states
        if item.projection.pattern_id == "gartley"
        and item.projection.node_indices == (10, 30, 50, 70)
    ]

    assert target_states
    assert target_states[0].state == "invalidated"
    assert target_states[0].closed_bar == 75
    assert target_states[0].reason == "confirmed_c_extreme_breached_before_terminal"
    assert not any(
        item.pattern_id == "gartley"
        and item.source_nodes == (10, 30, 50, 70)
        for item in scan.completions
    )


def test_expired_projection_cannot_be_completed_by_later_terminal_touch() -> None:
    frame = _gartley_path(terminal=True)

    scan = scan_source_completion_events(
        frame,
        scales=(3,),
        lifetime_bars=5,
    )
    target_states = [
        item
        for item in scan.states
        if item.projection.pattern_id == "gartley"
        and item.projection.node_indices == (10, 30, 50, 70)
    ]

    assert target_states
    assert target_states[0].state == "expired"
    assert target_states[0].closed_bar == target_states[0].projection.known_at + 5
    assert not any(
        item.pattern_id == "gartley"
        and item.source_nodes == (10, 30, 50, 70)
        for item in scan.completions
    )


def test_completed_terminal_is_immutable_when_future_tail_is_appended() -> None:
    frame = _gartley_path(terminal=True)
    prefix = frame.iloc[:96].reset_index(drop=True)

    prefix_scan = scan_source_completion_events(prefix, scales=(3,))
    full_scan = scan_source_completion_events(frame, scales=(3,))

    def terminal(scan):
        return next(
            item
            for item in scan.completions
            if item.pattern_id == "gartley"
            and item.source_nodes == (10, 30, 50, 70)
        )

    earlier = terminal(prefix_scan)
    later = terminal(full_scan)
    assert earlier.known_at == later.known_at
    assert earlier.terminal_bar == later.terminal_bar
    assert earlier.terminal_price == later.terminal_price


def test_same_bar_c_breach_and_terminal_is_fail_closed() -> None:
    frame = _gartley_path(terminal=True)
    frame.loc[80, "high"] = 185.0
    frame.loc[80, "low"] = 118.0

    scan = scan_source_completion_events(frame, scales=(3,))
    target_states = [
        item
        for item in scan.states
        if item.projection.pattern_id == "gartley"
        and item.projection.node_indices == (10, 30, 50, 70)
    ]

    assert target_states
    assert target_states[0].state == "invalidated"
    assert target_states[0].closed_bar == 80
    assert not any(
        item.pattern_id == "gartley"
        and item.source_nodes == (10, 30, 50, 70)
        for item in scan.completions
    )


def test_gap_through_source_prz_is_not_terminal_completion() -> None:
    frame = _gartley_path(terminal=True)
    frame.loc[90, "high"] = 119.0
    prefix = frame.iloc[:91].reset_index(drop=True)

    scan = scan_source_completion_events(prefix, scales=(3,))
    target_states = [
        item
        for item in scan.states
        if item.projection.pattern_id == "gartley"
        and item.projection.node_indices == (10, 30, 50, 70)
    ]

    assert target_states
    assert target_states[0].state == "invalidated"
    assert target_states[0].reason == "unobserved_far_side_passage_retired_policy_v2"
    assert target_states[0].audit.first_prz_entry_bar is None
    assert target_states[0].audit.terminal_bar is None
    assert not any(
        item.pattern_id == "gartley"
        and item.source_nodes == (10, 30, 50, 70)
        for item in scan.completions
    )


def test_terminal_requires_actual_tests_of_all_zone_measurements() -> None:
    projection = next(p for p in event_sourced_hierarchical_xabc_projections(
        _gartley_path(terminal=True), scales=(3,)) if p.pattern_id == "gartley")
    # Independent numbers: PRZ [119.57, 121.4]. First bar reaches the far end,
    # but skips the near boundary. Second tests near side only; third retests all.
    frame = pd.DataFrame({"low": [130, 118, 120, 119], "high": [131, 120, 122, 122]})
    for end in (1, 2, 3):
        audit = _recognition_source_execution(
            frame, signal_bar=0, direction=projection.direction, prz=projection.prz,
            reaction_anchor_price=200, observation_end_bar=end,
        )
        assert audit.terminal_bar == (3 if end == 3 else None)


def _market_completion_scan():
    from htcn.harmonic.models import HarmonicPoint
    from htcn.harmonic.prz import build_xabcd_prz
    from htcn.harmonic.rules import CARNEY_RULES
    from htcn.harmonic.source_completion import (
        SourceCompletionEvent,
        SourceCompletionScan,
        SourceProjection,
        _projection_state,
    )

    path = Path(__file__).resolve().parents[2] / "research/recognition-gate4c-case-evidence-v1.json"
    events = []
    for case in json.loads(path.read_text())["cases"]:
        if case["selection_group"] != "same_abc_different_x":
            continue
        points = tuple(HarmonicPoint(label=n["label"], index=n["index"], price=n["price"])
                       for n in case["nodes"])
        prz = build_xabcd_prz(CARNEY_RULES[case["pattern_id"]], points)
        projection = SourceProjection(case["pattern_id"], prz.direction, points,
                                      case["known_at"], prz, (), case["min_skipped_pivots"])
        # Only post-birth rows are consumed. Keep original positional indices.
        frame = pd.DataFrame(index=range(case["terminal_bar"] + 1), columns=["low", "high"],
                             dtype=float)
        for row in case["observation_rows"]:
            frame.loc[row["index"], ["low", "high"]] = [row["low"], row["high"]]
        state = _projection_state(frame, projection, lifetime_bars=180)
        assert state.state == "completed"
        events.append(SourceCompletionEvent(projection, state.audit))
    return SourceCompletionScan((), (), tuple(events), 0, 0, 0)


def test_market_multi_x_is_one_observation_with_all_interpretations() -> None:
    scan = _market_completion_scan()
    assert len(scan.completions) == 3
    groups = scan.completion_groups
    assert len(groups) == 1
    assert groups[0].key == ("bullish", (590, 597, 601), 631)
    assert {e.source_nodes[0] for e in groups[0].interpretations} == {544, 555, 565}
    assert all(not e.qualification.validated_identity for e in groups[0].interpretations)
    assert replace(scan, completions=tuple(reversed(scan.completions))).completion_groups == groups
    # Exact replay is idempotent; different X evidence is not discarded.
    assert replace(scan, completions=scan.completions * 2).completion_groups == groups


def test_grouping_keeps_distinct_abc_and_terminal_observations() -> None:
    scan = _market_completion_scan()
    event = scan.completions[0]
    other_points = tuple(replace(p, index=p.index + 1) for p in event.projection.points)
    other_abc = replace(event, projection=replace(event.projection, points=other_points))
    other_projection = replace(event.projection, points=(
        replace(event.projection.points[0], index=556), *event.projection.points[1:]))
    other_terminal = replace(event, projection=other_projection,
                             audit=replace(event.audit, terminal_bar=632,
                                                 execution_start_bar=633))
    extended = replace(scan, completions=(*scan.completions, other_abc, other_terminal))
    assert len(extended.completion_groups) == 3
    assert sum(len(g.interpretations) for g in extended.completion_groups) == 5
    # A later observation never changes the key of the already observed group.
    assert scan.completion_groups[0].key in {g.key for g in extended.completion_groups}


def test_grouping_rejects_conflicting_replay_instead_of_choosing_a_winner() -> None:
    scan = _market_completion_scan()
    event = scan.completions[0]
    conflict = replace(event, audit=replace(event.audit, terminal_price=event.terminal_price - 1))
    try:
        _ = replace(scan, completions=(*scan.completions, conflict)).completion_groups
    except ValueError as error:
        assert "conflicting completion" in str(error)
    else:
        raise AssertionError("conflicting replay must not be silently deduplicated")


def test_grouping_preserves_competing_family_without_identity_promotion() -> None:
    scan = _market_completion_scan()
    event = scan.completions[0]
    # Grouping must not choose a family; this is a transport-level label variant,
    # not a claim that these Bat points satisfy Gartley rules.
    alternative = replace(event, projection=replace(event.projection, pattern_id="gartley"))
    grouped = replace(scan, completions=(*scan.completions, alternative)).completion_groups
    assert len(grouped) == 1
    assert len(grouped[0].interpretations) == 4
    assert {e.pattern_id for e in grouped[0].interpretations} == {"bat", "gartley"}
