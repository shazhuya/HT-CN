import json
from pathlib import Path

from htcn.harmonic.confluence_audit import audit_projection_confluence
from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.prz import build_xabcd_prz
from htcn.harmonic.rules import CARNEY_RULES


def _cases():
    path = Path(__file__).resolve().parents[2] / "research/recognition-gate4c-case-evidence-v1.json"
    return json.loads(path.read_text())["cases"]


def test_frozen_market_cases_distinguish_review_from_identity() -> None:
    for case in _cases():
        points = tuple(HarmonicPoint(label=n["label"], index=n["index"], price=n["price"])
                       for n in case["nodes"])
        prz = build_xabcd_prz(CARNEY_RULES[case["pattern_id"]], points)
        result = audit_projection_confluence(case["pattern_id"], points, prz)
        expected = ("review_required" if case["selection_group"] == "wide_crab"
                    else "primary_compatible_unverified")
        assert result.status == expected
        assert not result.validated_identity
        assert abs(result.required_bc_at_nominal_xa - case["required_bc_ratio_at_exact_xa"]) < 1e-9


def test_primary_screen_is_price_scale_and_mirror_invariant() -> None:
    for case in _cases():
        results = []
        for multiplier, offset in [(1, 0), (10, 100), (-1, 1000)]:
            points = tuple(HarmonicPoint(label=n["label"], index=n["index"],
                                        price=multiplier * n["price"] + offset)
                           for n in case["nodes"])
            prz = build_xabcd_prz(CARNEY_RULES[case["pattern_id"]], points)
            results.append(audit_projection_confluence(case["pattern_id"], points, prz))
        assert len({r.status for r in results}) == 1
        assert max(r.required_bc_at_nominal_xa for r in results) - min(
            r.required_bc_at_nominal_xa for r in results) < 1e-9
