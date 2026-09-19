from __future__ import annotations

import pandas as pd

import htcn.harmonic.rsi_bamm_lifecycle as lifecycle
from htcn.harmonic.rsi_bamm import (
    RSIBammDirection,
    RSIBammProfile,
    RSIBammRelation,
    RSIBammSequence,
    RSIBammStructure,
    RSIBammStructureKind,
)


def _frame(size: int = 12) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "close": [100.0 + index for index in range(size)],
            "low": [99.0 + index for index in range(size)],
            "high": [101.0 + index for index in range(size)],
        }
    )


def _sequence(*, completion_bar: int) -> RSIBammSequence:
    direction = RSIBammDirection.BULLISH
    first = RSIBammStructure(
        direction=direction,
        kind=RSIBammStructureKind.IMPULSIVE,
        enter_bar=1,
        exit_bar=3,
        rsi_extreme_bar=2,
        rsi_extreme_value=24.0,
        price_extreme_bar=2,
        price_extreme_value=90.0,
        exit_rsi=35.0,
    )
    second = RSIBammStructure(
        direction=direction,
        kind=RSIBammStructureKind.IMPULSIVE,
        enter_bar=completion_bar - 2,
        exit_bar=completion_bar,
        rsi_extreme_bar=completion_bar - 1,
        rsi_extreme_value=27.0,
        price_extreme_bar=completion_bar - 1,
        price_extreme_value=88.0,
        exit_rsi=35.0,
    )
    return RSIBammSequence(
        direction=direction,
        profile=RSIBammProfile.SIMPLE_DIVERGENCE,
        relation=RSIBammRelation.DIVERGENCE,
        first_structure=first,
        midpoint_bar=4,
        midpoint_rsi=52.0,
        second_structure=second,
        trigger_bar=3,
        trigger_reference_price=91.0,
        trigger_to_prior_price_extreme_bars=1,
        confirmation_extension_ratio=1.13,
        confirmation_extension_basis="trigger_bar_is_not_prior_price_extreme",
        reaction_anchor_bar=4,
        reaction_anchor_price=100.0,
        confirmation_projection_price=88.7,
        price_projection_resolved=True,
        price_projection_tested=True,
    )


def test_source_clock_does_not_see_future_bamm(monkeypatch) -> None:
    sequence = _sequence(completion_bar=8)
    observed_lengths: list[int] = []

    def fake_scan(frame, *, direction):
        observed_lengths.append(len(frame))
        return [] if len(frame) <= 7 else [sequence]

    monkeypatch.setattr(lifecycle, "scan_rsi_bamm_frame", fake_scan)
    evidence = lifecycle.audit_rsi_bamm_at_source_clock(
        _frame(), direction="bullish", source_clock_bar=6
    )

    assert observed_lengths == [7]
    assert evidence.status == "no_completed_rsi_bamm_observed"
    assert evidence.source_confirmed is False
    assert evidence.mutates_harmonic_identity is False


def test_later_bamm_is_not_backdated_to_terminal_bar(monkeypatch) -> None:
    sequence = _sequence(completion_bar=8)
    monkeypatch.setattr(lifecycle, "scan_rsi_bamm_frame", lambda frame, *, direction: [sequence])

    evidence = lifecycle.audit_rsi_bamm_at_source_clock(
        _frame(), direction="bullish", source_clock_bar=6, observed_through_bar=9
    )

    assert evidence.latest_completion_bar == 8
    assert evidence.evidence_available_at_source_clock is False
    assert evidence.status == "rsi_bamm_completed_after_source_clock"
    assert evidence.source_confirmed is False


def test_completed_bamm_can_be_visible_at_source_clock_without_claiming_confluence(monkeypatch) -> None:
    sequence = _sequence(completion_bar=6)
    monkeypatch.setattr(lifecycle, "scan_rsi_bamm_frame", lambda frame, *, direction: [sequence])

    evidence = lifecycle.audit_rsi_bamm_at_source_clock(
        _frame(), direction="bullish", source_clock_bar=6
    )

    assert evidence.evidence_available_at_source_clock is True
    assert evidence.latest_profile == "simple_divergence"
    assert evidence.latest_projection_tested is True
    assert evidence.status == "rsi_bamm_available_at_source_clock"
    # Lifecycle visibility alone cannot manufacture harmonic confluence.
    assert evidence.source_confirmed is False


def test_source_clock_validation_fails_closed() -> None:
    frame = _frame()
    try:
        lifecycle.audit_rsi_bamm_at_source_clock(frame, direction="bullish", source_clock_bar=-1)
    except ValueError as exc:
        assert "source_clock_bar" in str(exc)
    else:
        raise AssertionError("negative source clock must fail")

    try:
        lifecycle.audit_rsi_bamm_at_source_clock(
            frame, direction="bullish", source_clock_bar=6, observed_through_bar=5
        )
    except ValueError as exc:
        assert "cannot precede" in str(exc)
    else:
        raise AssertionError("backward observation window must fail")
