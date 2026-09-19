from __future__ import annotations

import pandas as pd

from htcn.harmonic.execution import observe_source_execution
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.prz import PotentialReversalZone, PRZComponent
from htcn.harmonic.source_lifecycle import SourceLifecycleState, derive_source_lifecycle


def _prz(*, frozen: bool = True) -> PotentialReversalZone:
    component = PRZComponent(
        name="source-lifecycle-test",
        price_low=90.0,
        price_high=100.0,
        ratio_low=1.0,
        ratio_high=1.0,
    )
    return PotentialReversalZone(
        pattern_id="gartley",
        direction=PatternDirection.BULLISH,
        components=(component,),
        source_prz_low=90.0 if frozen else None,
        source_prz_high=100.0 if frozen else None,
    )


def _transition_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "high": [122, 116, 108, 103, 101, 96, 99, 102, 105, 104, 99, 103],
            "low": [118, 110, 102, 95, 94, 89, 93, 101, 103, 99, 89, 101],
            "close": [120, 113, 105, 98, 97, 92, 96, 101.5, 104, 100, 92, 102],
        }
    )


def _state_for_prefix(frame: pd.DataFrame, end_bar: int) -> SourceLifecycleState:
    prefix = frame.iloc[: end_bar + 1].reset_index(drop=True)
    audit = observe_source_execution(
        prefix,
        signal_bar=1,
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        reaction_anchor_price=120.0,
    )
    return derive_source_lifecycle(prefix, audit).state


def test_source_lifecycle_prefixes_never_backdate_future_transitions() -> None:
    frame = _transition_frame()

    assert _state_for_prefix(frame, 2) is SourceLifecycleState.APPROACHING_SOURCE_PRZ
    assert _state_for_prefix(frame, 3) is SourceLifecycleState.ENTERED_SOURCE_PRZ
    assert _state_for_prefix(frame, 4) is SourceLifecycleState.WAITING_TERMINAL
    assert _state_for_prefix(frame, 5) is SourceLifecycleState.SOURCE_TERMINAL_COMPLETE
    assert _state_for_prefix(frame, 6) is SourceLifecycleState.T_PLUS_1
    assert _state_for_prefix(frame, 7) is SourceLifecycleState.TYPE_I_CONFIRMED
    assert _state_for_prefix(frame, 8) is SourceLifecycleState.TYPE_I_CONFIRMED
    assert _state_for_prefix(frame, 9) is SourceLifecycleState.TYPE_II_RETEST_FORMING
    assert _state_for_prefix(frame, 10) is SourceLifecycleState.TYPE_II_TERMINAL
    assert _state_for_prefix(frame, 11) is SourceLifecycleState.REVERSAL_EVIDENCE

    # Earlier prefixes must never inherit the later Type-II/reversal states.
    assert _state_for_prefix(frame, 6) is not SourceLifecycleState.TYPE_II_RETEST_FORMING
    assert _state_for_prefix(frame, 9) is not SourceLifecycleState.TYPE_II_TERMINAL
    assert _state_for_prefix(frame, 10) is not SourceLifecycleState.REVERSAL_EVIDENCE


def test_source_lifecycle_fails_closed_when_source_prz_is_unresolved() -> None:
    frame = _transition_frame().iloc[:6].reset_index(drop=True)
    audit = observe_source_execution(
        frame,
        signal_bar=1,
        direction=PatternDirection.BULLISH,
        prz=_prz(frozen=False),
        reaction_anchor_price=120.0,
    )
    snapshot = derive_source_lifecycle(frame, audit)

    assert snapshot.state is SourceLifecycleState.SOURCE_PRZ_UNRESOLVED
    assert snapshot.source_prz_low is None
    assert snapshot.source_prz_high is None
    assert snapshot.retrospective_geometry_clock_used is False


def test_type_i_failed_is_an_execution_state_not_pattern_invalidation() -> None:
    frame = pd.DataFrame(
        {
            "high": [120, 105, 96, 99, 99, 98, 99, 98, 99],
            "low": [116, 101, 89, 92, 93, 92, 93, 92, 93],
            "close": [118, 103, 92, 96, 96, 95, 96, 95, 96],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=0,
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        reaction_anchor_price=120.0,
    )
    snapshot = derive_source_lifecycle(frame, audit)

    assert snapshot.source_terminal_bar == 2
    assert snapshot.bars_since_terminal == 6
    assert snapshot.type_i_t1_bar is None
    assert snapshot.state is SourceLifecycleState.TYPE_I_FAILED
    assert snapshot.state is not SourceLifecycleState.INVALIDATED
    assert snapshot.retrospective_geometry_clock_used is False


def test_late_38_2_reaction_is_reaction_only_not_early_type_i_confirmation() -> None:
    frame = pd.DataFrame(
        {
            "high": [120, 105, 96, 99, 99, 99, 99, 99, 102],
            "low": [116, 101, 89, 92, 93, 92, 93, 92, 91],
            "close": [118, 103, 92, 96, 96, 96, 96, 96, 101],
        }
    )
    audit = observe_source_execution(
        frame,
        signal_bar=0,
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        reaction_anchor_price=120.0,
    )
    snapshot = derive_source_lifecycle(frame, audit)

    assert snapshot.source_terminal_bar == 2
    assert snapshot.type_i_t1_bar == 8
    assert snapshot.type_i_t1_bar - snapshot.source_terminal_bar == 6
    assert snapshot.state is SourceLifecycleState.REACTION_ONLY
