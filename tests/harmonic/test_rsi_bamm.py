from dataclasses import replace

import pandas as pd

from htcn.harmonic.rsi_bamm import (
    RSI_BAMM_PERIOD,
    RSIBammDirection,
    RSIBammProfile,
    RSIBammRelation,
    RSIBammStructureKind,
    confirm_rsi_bamm,
    scan_rsi_bamm_frame,
    scan_rsi_bamm_values,
)


def _highs_from_lows(lows: list[float]) -> list[float]:
    return [value + 1.0 for value in lows]


def test_bullish_simple_confirmation_requires_two_impulses_and_midpoint() -> None:
    rsi = [55, 29, 25, 31, 42, 51, 44, 29, 27, 31]
    lows = [110, 100, 90, 92, 95, 97, 98, 99, 95, 96]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.profile is RSIBammProfile.SIMPLE_CONFIRMATION
    assert row.relation is RSIBammRelation.CONFIRMATION
    assert row.first_structure.kind is RSIBammStructureKind.IMPULSIVE
    assert row.second_structure.kind is RSIBammStructureKind.IMPULSIVE
    assert row.midpoint_bar == 5
    assert row.midpoint_rsi == 51
    assert row.completion_bar == 9
    assert row.confirmation_extension_ratio == 1.13
    assert row.price_projection_resolved is False
    assert row.mutates_harmonic_identity is False


def test_bullish_simple_divergence_has_lower_price_but_higher_rsi_low() -> None:
    rsi = [55, 29, 25, 31, 45, 52, 44, 29, 27, 31]
    lows = [110, 100, 90, 92, 95, 97, 98, 93, 88, 89]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )

    assert len(rows) == 1
    assert rows[0].profile is RSIBammProfile.SIMPLE_DIVERGENCE
    assert rows[0].relation is RSIBammRelation.DIVERGENCE
    assert rows[0].first_structure.rsi_extreme_value == 25
    assert rows[0].second_structure.rsi_extreme_value == 27
    assert rows[0].second_structure.price_extreme_value == 88


def test_bullish_complex_divergence_starts_with_w_and_ends_impulsive() -> None:
    rsi = [55, 29, 20, 26, 22, 31, 45, 52, 43, 29, 24, 31]
    lows = [110, 100, 90, 94, 91, 93, 96, 98, 97, 92, 88, 89]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )

    assert len(rows) == 1
    row = rows[0]
    assert row.profile is RSIBammProfile.COMPLEX_DIVERGENCE
    assert row.first_structure.kind is RSIBammStructureKind.COMPLEX
    assert row.second_structure.kind is RSIBammStructureKind.IMPULSIVE
    assert row.first_structure.rsi_extreme_value == 20
    assert row.second_structure.rsi_extreme_value == 24


def test_bearish_simple_confirmation_is_mirror_image() -> None:
    rsi = [45, 71, 80, 69, 58, 49, 60, 71, 76, 69]
    highs = [90, 110, 120, 118, 116, 114, 113, 112, 115, 114]
    lows = [value - 1.0 for value in highs]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=highs,
        direction=RSIBammDirection.BEARISH,
    )

    assert len(rows) == 1
    assert rows[0].profile is RSIBammProfile.SIMPLE_CONFIRMATION
    assert rows[0].relation is RSIBammRelation.CONFIRMATION
    assert rows[0].midpoint_bar == 5
    assert rows[0].first_structure.rsi_extreme_value == 80
    assert rows[0].second_structure.rsi_extreme_value == 76


def test_bearish_simple_divergence_has_higher_price_but_lower_rsi_high() -> None:
    rsi = [45, 71, 80, 69, 58, 49, 60, 71, 76, 69]
    highs = [90, 110, 120, 118, 116, 114, 113, 121, 125, 124]
    lows = [value - 1.0 for value in highs]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=highs,
        direction=RSIBammDirection.BEARISH,
    )

    assert len(rows) == 1
    assert rows[0].profile is RSIBammProfile.SIMPLE_DIVERGENCE
    assert rows[0].relation is RSIBammRelation.DIVERGENCE


def test_midpoint_50_is_absolute_hard_gate() -> None:
    rsi = [55, 29, 25, 31, 42, 29, 27, 31, 45]
    lows = [110, 100, 90, 92, 95, 93, 88, 89, 94]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )
    assert rows == []


def test_complex_secondary_retest_does_not_pass_bamm_type_contract() -> None:
    rsi = [55, 29, 25, 31, 45, 52, 43, 29, 24, 27, 25, 31]
    lows = [110, 100, 90, 92, 95, 97, 98, 94, 91, 93, 88, 90]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )
    assert rows == []


def test_no_lookahead_sequence_appears_only_when_second_impulse_exits_extreme() -> None:
    rsi = [55, 29, 25, 31, 42, 51, 44, 29, 27, 31]
    lows = [110, 100, 90, 92, 95, 97, 98, 93, 88, 89]

    before_exit = scan_rsi_bamm_values(
        rsi[:-1],
        lows=lows[:-1],
        highs=_highs_from_lows(lows[:-1]),
        direction=RSIBammDirection.BULLISH,
    )
    at_exit = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )

    assert before_exit == []
    assert len(at_exit) == 1
    assert at_exit[0].completion_bar == len(rsi) - 1


def test_trigger_bar_at_prior_price_extreme_selects_1618_without_inventing_target() -> None:
    rsi = [55, 29, 25, 31, 42, 51, 44, 29, 27, 31]
    lows = [110, 100, 92, 90, 95, 97, 98, 99, 95, 96]
    rows = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )

    assert len(rows) == 1
    assert rows[0].trigger_bar == 3
    assert rows[0].first_structure.price_extreme_bar == 3
    assert rows[0].confirmation_extension_ratio == 1.618
    assert rows[0].confirmation_extension_basis == "trigger_bar_is_prior_price_extreme"
    assert rows[0].price_projection_resolved is False


def test_final_confirmation_fails_closed_while_xa_projection_is_unresolved() -> None:
    rsi = [55, 29, 25, 31, 42, 51, 44, 29, 27, 31]
    lows = [110, 100, 90, 92, 95, 97, 98, 99, 95, 96]
    sequence = scan_rsi_bamm_values(
        rsi,
        lows=lows,
        highs=_highs_from_lows(lows),
        direction=RSIBammDirection.BULLISH,
    )[0]

    blocked = confirm_rsi_bamm(
        sequence,
        price_confirmation_tested=True,
        harmonic_pattern_completed=True,
    )
    assert blocked.source_confirmed is False
    assert blocked.status == "source_confirmation_blocked_projection_unresolved"

    source_resolved = replace(sequence, price_projection_resolved=True)
    confirmed = confirm_rsi_bamm(
        source_resolved,
        price_confirmation_tested=True,
        harmonic_pattern_completed=True,
    )
    assert confirmed.source_confirmed is True


def test_frame_wrapper_rejects_missing_ohlc_and_keeps_period_contract() -> None:
    try:
        scan_rsi_bamm_frame(
            pd.DataFrame({"close": [1.0, 2.0, 3.0]}),
            direction=RSIBammDirection.BULLISH,
            period=RSI_BAMM_PERIOD,
        )
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("expected ValueError")
