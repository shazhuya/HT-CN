from __future__ import annotations

import json
from pathlib import Path

import pytest

from htcn.harmonic.ratios import RECIPROCAL_ABCD
from htcn.harmonic.rules import CARNEY_RULES
from htcn.harmonic.source_prz import SOURCE_PRZ_PROFILES
from htcn.harmonic.source_prz_evidence import SOURCE_PRZ_EVIDENCE


ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / "research" / "book-source-prz-cases-v1.json"


def _payload() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def _ratio_in(values: tuple[float, ...], target: float) -> bool:
    """Match printed source ratios to canonical internal precision.

    Carney's prose/figure labels sometimes print a derived ratio as 1.41 while the canonical
    registry stores sqrt(2) rounded to 1.414. Keep the book value verbatim in the ledger and
    allow only a narrow display-rounding tolerance here; this is not a trading tolerance.
    """
    return any(float(value) == pytest.approx(float(target), rel=0, abs=0.005) for value in values)


def test_book_ledger_has_market_evidence_for_each_executable_source_prz_family() -> None:
    cases = _payload()["cases"]
    by_pattern: dict[str, list[dict]] = {}
    for case in cases:
        by_pattern.setdefault(case["pattern_id"], []).append(case)

    for pattern_id in ("abcd", "gartley", "bat", "butterfly", "crab", "deep_crab"):
        if pattern_id != "abcd":
            assert SOURCE_PRZ_PROFILES[pattern_id].status == "frozen"
        assert by_pattern.get(pattern_id), f"missing market case for {pattern_id}"
        evidence = SOURCE_PRZ_EVIDENCE[pattern_id]
        assert evidence.market_case_ids
        assert set(evidence.market_case_ids).issubset({case["case_id"] for case in by_pattern[pattern_id]})
        assert evidence.evidence_level.startswith("source_specification_plus_market_examples")


def test_every_ledger_component_belongs_to_the_registered_source_family() -> None:
    reciprocal_bc_values = tuple(
        float(value) for values in RECIPROCAL_ABCD.values() for value in values
    )
    for case in _payload()["cases"]:
        pattern_id = case["pattern_id"]
        if pattern_id == "abcd":
            for component in case["source_components"]:
                kind = component["kind"]
                ratio = float(component["ratio"])
                if kind == "abcd":
                    assert ratio == pytest.approx(1.0)
                elif kind == "bc":
                    assert _ratio_in(reciprocal_bc_values, ratio)
                else:
                    raise AssertionError(f"unexpected standalone AB=CD ledger component: {kind}")
            continue

        profile = SOURCE_PRZ_PROFILES[pattern_id]
        rule = CARNEY_RULES[pattern_id]
        d_xa = rule.constraints.get("d_xa")

        for component in case["source_components"]:
            kind = component["kind"]
            ratio = float(component["ratio"])
            if kind == "xa":
                assert d_xa is not None
                assert d_xa.contains(ratio), f"{case['case_id']} XA {ratio} outside registered D/XA"
            elif kind == "bc":
                assert _ratio_in(profile.bc_ratios, ratio), (
                    f"{case['case_id']} BC {ratio} missing from {pattern_id} source family"
                )
            elif kind == "abcd":
                assert _ratio_in(profile.abcd_ratios, ratio), (
                    f"{case['case_id']} AB=CD {ratio} missing from {pattern_id} source family"
                )
            else:
                raise AssertionError(f"unknown ledger component kind: {kind}")


def test_book_ledger_distinguishes_membership_evidence_from_coordinate_selector_oracles() -> None:
    payload = _payload()
    assert "does not invent" in payload["scope"]
    assert all(case["coordinate_regression_eligible"] is False for case in payload["cases"])
    assert any("coordinates" in item.lower() for item in payload["known_open_items"])


def test_abcd_book_cases_freeze_exact_completion_as_defining_measure() -> None:
    cases = [case for case in _payload()["cases"] if case["pattern_id"] == "abcd"]
    assert len(cases) >= 2
    for case in cases:
        defining = [item for item in case["source_components"] if item["role"] == "defining"]
        assert defining == [
            next(item for item in case["source_components"] if item["kind"] == "abcd")
        ]
        assert defining[0]["ratio"] == pytest.approx(1.0)
        assert any(item["kind"] == "bc" for item in case["source_components"])
    evidence = SOURCE_PRZ_EVIDENCE["abcd"]
    assert evidence.selection_authority == "carney_exact_abcd_plus_primary_reciprocal_bc"


def test_perfect_bat_source_tension_is_recorded_not_silently_resolved() -> None:
    payload = _payload()
    ara = next(case for case in payload["cases"] if case["case_id"] == "v1-perfect-bat-ara-weekly")
    evidence = SOURCE_PRZ_EVIDENCE["bat"]

    assert "known_source_tension" in ara["evidence_level"]
    assert "do not all share one exact algebraic D" in ara["known_source_tension"]
    assert evidence.known_tensions
    assert "do not all share one exact D" in evidence.known_tensions[0]
    assert evidence.coordinate_regression_status == "pending_reliable_source_pivots"


def test_source_conflict_profile_does_not_gain_market_case_evidence_by_accident() -> None:
    profile = SOURCE_PRZ_PROFILES["alternate_bat"]
    evidence = SOURCE_PRZ_EVIDENCE["alternate_bat"]
    assert profile.status == "source_conflict"
    assert evidence.market_case_ids == ()
    assert evidence.selection_authority == "none_fail_closed"
    assert evidence.coordinate_regression_status == "blocked_by_source_conflict"
