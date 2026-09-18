from __future__ import annotations

from dataclasses import asdict

import pandas as pd
import pytest

from htcn.app.source_aligned_service import SourceAlignedHarmonicService
from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.harmonic.models import HarmonicPoint, PatternState
from htcn.harmonic.rsi_bamm_confluence import observe_source_execution_for_match
from htcn.harmonic.shark import SharkMatch, evaluate_shark
from htcn.harmonic.shark_source import build_shark_source_contract


def _frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"high": 101.0, "low": 99.0, "close": 100.0},
            {"high": 121.0, "low": 119.0, "close": 120.0},
            {"high": 111.0, "low": 109.0, "close": 110.0},
            {"high": 125.0, "low": 123.0, "close": 124.0},
            {"high": 123.0, "low": 120.0, "close": 121.0},
            {"high": 110.0, "low": 104.0, "close": 106.0},
            {"high": 100.0, "low": 96.88, "close": 98.0},
        ]
    )


def _forming_payload() -> dict:
    points = (
        HarmonicPoint("0", 0, 100.0),
        HarmonicPoint("X", 1, 120.0),
        HarmonicPoint("A", 2, 110.0),
        HarmonicPoint("B", 3, 124.0),
    )
    contract = build_shark_source_contract(points)
    return {
        "pattern_id": "shark",
        "schema": "0XABC",
        "direction": "bullish",
        "state": "forming",
        "scale": 1,
        "points": [asdict(point) for point in points],
        "prz": SourceAlignedHarmonicService._prz_payload(contract.prz),
    }


def test_forming_shark_gets_source_clock_and_lifecycle_from_b_anchor() -> None:
    frame = _frame()
    payload = _forming_payload()

    clock = M3SourceClockHarmonicService._execution_clock_from_forming_payload(
        payload,
        frame,
    )

    assert clock is not None
    assert clock["reaction_anchor_label"] == "B"
    assert clock["reaction_anchor_price"] == pytest.approx(124.0)
    assert clock["terminal_bar"] == 6
    assert clock["target_382"] == pytest.approx(96.88 + 0.382 * (124.0 - 96.88))
    assert clock["lifecycle"]["state"] == "source_terminal_complete"
    assert clock["lifecycle"]["source_terminal_bar"] == 6
    assert clock["type_i_target_semantics"] == (
        "generic_type_i_reaction_confirmation_only_not_shark_management_target"
    )
    management = clock["shark_management"]
    assert management["status"] == "source_terminal_observed"
    assert management["target_50_bc"] == pytest.approx(96.88 + 0.50 * (124.0 - 96.88))
    assert management["target_618_bc"] == pytest.approx(96.88 + 0.618 * (124.0 - 96.88))
    assert management["reciprocal_abcd"] == pytest.approx(96.88 + (124.0 - 110.0))
    assert management["initial_target"] == pytest.approx(management["reciprocal_abcd"])
    assert management["initial_target_basis"] == "reciprocal_abcd"


def test_completed_shark_source_clock_uses_b_not_a_as_type_i_span_anchor() -> None:
    points = (
        HarmonicPoint("0", 0, 100.0),
        HarmonicPoint("X", 1, 120.0),
        HarmonicPoint("A", 2, 110.0),
        HarmonicPoint("B", 3, 124.0),
        HarmonicPoint("C", 6, 96.88),
    )
    evaluation = evaluate_shark(points)
    assert evaluation.passed

    match = SharkMatch(
        pattern_id="shark",
        direction=evaluation.direction,
        state=PatternState.COMPLETED,
        scale=1,
        points=evaluation.points,
        evaluation=evaluation,
        geometry_score=evaluation.geometry_score,
        conflict_key=tuple(point.index for point in evaluation.points),
    )
    audit = observe_source_execution_for_match(_frame(), match)

    assert audit is not None
    assert audit.terminal_bar == 6
    assert audit.target_382 == pytest.approx(96.88 + 0.382 * (124.0 - 96.88))
    assert audit.target_382 != pytest.approx(96.88 + 0.382 * (110.0 - 96.88))
