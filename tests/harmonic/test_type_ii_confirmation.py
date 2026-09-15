import pandas as pd

from htcn.harmonic.lifecycle import audit_completed_reaction
from htcn.harmonic.models import HarmonicPoint, PatternDirection
from htcn.harmonic.prz import PRZComponent, PotentialReversalZone


def _points() -> tuple[HarmonicPoint, ...]:
    return (
        HarmonicPoint("X", 0, 100.0),
        HarmonicPoint("A", 1, 200.0),
        HarmonicPoint("B", 2, 140.0),
        HarmonicPoint("C", 3, 180.0),
        HarmonicPoint("D", 4, 120.0),
    )


def _prz() -> PotentialReversalZone:
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
    )


def test_type_ii_retest_records_price_and_rsi_confirmation_evidence() -> None:
    # D is at index 4. Price first exits the bullish PRZ at +1, retests its full lower
    # edge at +4, then exits in the reversal direction again at +5. With a short RSI
    # period for the deterministic fixture, the retest also contains an oversold reading
    # that subsequently reverses back above 30.
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

    assert audit.type_ii_candidate is True
    assert audit.first_prz_exit_bar == 1
    assert audit.secondary_prz_retest_bar == 4
    assert audit.full_prz_retest_bar == 4
    assert audit.reversal_exit_after_retest_bar == 5
    assert audit.bars_to_reversal_exit_after_retest == 1
    assert audit.rsi_extreme_bar is not None
    assert audit.rsi_extreme_value is not None and audit.rsi_extreme_value <= 30.0
    assert audit.rsi_trigger_bar is not None
    assert audit.rsi_trigger_value is not None and audit.rsi_trigger_value > 30.0
    assert audit.rsi_confirmation is True
    assert audit.type_ii_evidence_state == "price_and_rsi_confirmed"


def test_type_ii_candidate_without_rsi_extreme_stays_price_only() -> None:
    frame = pd.DataFrame(
        {
            "close": [100, 110, 120, 130, 120, 130, 140, 150, 120, 130, 140, 150],
            "high": [101, 111, 121, 131, 121, 132, 142, 152, 121, 132, 142, 152],
            "low": [99, 109, 119, 129, 119, 128, 138, 148, 119, 128, 138, 148],
        }
    )
    audit = audit_completed_reaction(
        frame,
        points=_points(),
        direction=PatternDirection.BULLISH,
        prz=_prz(),
        rsi_period=3,
    )
    assert audit.type_ii_candidate is True
    assert audit.reversal_exit_after_retest_bar is not None
    assert audit.rsi_confirmation is False
    assert audit.type_ii_evidence_state == "price_confirmed_no_rsi"
