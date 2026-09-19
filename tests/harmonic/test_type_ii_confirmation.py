import pandas as pd

from htcn.harmonic.lifecycle import audit_completed_reaction
from htcn.harmonic.models import HarmonicPoint, PatternDirection
from htcn.harmonic.prz import PotentialReversalZone, PRZComponent


def _points() -> tuple[HarmonicPoint, ...]:
    return (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 1, 200.0),
        HarmonicPoint("B", 2, 140.0),
        HarmonicPoint("C", 3, 180.0),
        HarmonicPoint("D", 4, 120.0),
    )


def _prz(*, source_bounds: bool = True) -> PotentialReversalZone:
    component = PRZComponent(
        name="test",
        ratio_low=1.0,
        ratio_high=1.0,
        price_low=118.0,
        price_high=122.0,
    )
    return PotentialReversalZone(
        pattern_id="test",
        direction=PatternDirection.BULLISH,
        components=(component,),
        source_prz_low=118.0 if source_bounds else None,
        source_prz_high=122.0 if source_bounds else None,
    )


def test_type_ii_full_retest_records_price_and_rsi_confirmation_evidence() -> None:
    # D is at index 4. Price first exits the bullish source PRZ at +1, later returns
    # through the full lower/terminal side at +4, then exits again at +5.
    close = [200, 190, 180, 170, 120, 130, 140, 150, 119, 126, 138, 146]
    frame = pd.DataFrame(
        {
            "close": close,
            "high": [201, 191, 181, 181, 121, 132, 142, 152, 121, 128, 140, 148],
            "low": [199, 189, 179, 169, 119, 128, 138, 148, 117, 124, 136, 144],
        }
    )

    audit = audit_completed_reaction(
        frame,
        points=_points(),
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        rsi_period=3,
    )

    assert audit.source_prz_available is True
    assert audit.type_ii_candidate is True
    assert audit.first_prz_exit_bar == 1
    assert audit.secondary_prz_retest_bar == 4
    assert audit.full_prz_retest_bar == 4
    assert audit.type_ii_terminal_bar == 4
    assert audit.reversal_exit_after_retest_bar == 5
    assert audit.bars_to_reversal_exit_after_retest == 1
    assert audit.rsi_extreme_bar is not None
    assert audit.rsi_extreme_value is not None and audit.rsi_extreme_value <= 30.0
    assert audit.rsi_trigger_bar is not None
    assert audit.rsi_trigger_value is not None and audit.rsi_trigger_value > 30.0
    assert audit.rsi_confirmation is True
    assert audit.indicator_evidence_kind == "wilder_rsi_extreme_reversal"
    assert audit.indicator_evidence_is_rsi_bamm is False
    assert audit.type_ii_evidence_state == "price_and_rsi_confirmed"


def test_type_ii_full_retest_without_rsi_extreme_stays_price_only() -> None:
    frame = pd.DataFrame(
        {
            "close": [100, 110, 120, 130, 120, 130, 140, 150, 120, 130, 140, 150],
            "high": [101, 111, 121, 131, 121, 132, 142, 152, 121, 132, 142, 152],
            "low": [99, 109, 119, 129, 119, 128, 138, 148, 117, 128, 138, 148],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=_points(),
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        rsi_period=3,
    )
    assert audit.source_prz_available is True
    assert audit.type_ii_candidate is True
    assert audit.full_prz_retest_bar is not None
    assert audit.reversal_exit_after_retest_bar is not None
    assert audit.rsi_confirmation is False
    assert audit.type_ii_evidence_state == "price_confirmed_no_rsi"


def test_partial_source_prz_overlap_is_not_promoted_to_type_ii_candidate() -> None:
    # +1 exits source PRZ. +4 overlaps its upper half (low=120 > 118), then price exits.
    # This is not a full retest of the source PRZ terminal side.
    frame = pd.DataFrame(
        {
            "close": [100, 110, 120, 130, 120, 130, 140, 150, 121, 130, 140, 150],
            "high": [101, 111, 121, 131, 121, 132, 142, 152, 123, 132, 142, 152],
            "low": [99, 109, 119, 129, 119, 128, 138, 148, 120, 128, 138, 148],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=_points(),
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        rsi_period=3,
    )

    assert audit.secondary_prz_retest_bar == 4
    assert audit.source_prz_available is True
    assert audit.full_prz_retest_bar is None
    assert audit.type_ii_terminal_bar is None
    assert audit.type_ii_candidate is False
    assert audit.reversal_exit_after_retest_bar is None
    assert audit.rsi_confirmation is False
    assert audit.type_ii_evidence_state == "partial_retest_only"


def test_missing_source_prz_fails_closed_even_when_ideal_core_is_retested() -> None:
    # The same path would touch the legacy ideal core, but no source Raw PRZ has been
    # frozen. The audit may record a descriptive re-entry; it must not manufacture a
    # full retest or Type-II candidate from the ideal core/component envelope.
    frame = pd.DataFrame(
        {
            "close": [100, 110, 120, 130, 120, 130, 140, 150, 119, 130, 140, 150],
            "high": [101, 111, 121, 131, 121, 132, 142, 152, 121, 132, 142, 152],
            "low": [99, 109, 119, 129, 119, 128, 138, 148, 117, 128, 138, 148],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=_points(),
        direction=PatternDirection.BULLISH,
        prz=_prz(source_bounds=False),
        rsi_period=3,
    )

    assert audit.source_prz_available is False
    assert audit.secondary_prz_retest_bar is not None
    assert audit.full_prz_retest_bar is None
    assert audit.type_ii_terminal_bar is None
    assert audit.type_ii_candidate is False
    assert audit.reversal_exit_after_retest_bar is None
    assert audit.rsi_confirmation is False
    assert audit.type_ii_evidence_state == "source_prz_unresolved"
