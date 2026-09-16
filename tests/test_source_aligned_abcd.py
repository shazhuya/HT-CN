from __future__ import annotations

from htcn.app.source_aligned_service import SourceAlignedHarmonicService
from htcn.harmonic.abcd import project_forming_abcd
from htcn.harmonic.models import HarmonicPoint


def test_source_aligned_api_exposes_abcd_source_raw_prz_not_ideal_alias() -> None:
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 161.8),
    )
    projection = project_forming_abcd(points)
    assert projection is not None

    payload = SourceAlignedHarmonicService._prz_payload(projection.prz)
    source = payload["source_prz"]

    assert payload["semantics_version"] == 3
    assert payload["legacy_price_semantics"] == "ideal_core"
    assert source["available"] is True
    assert source["component_names"] == ["AB=CD x1", "BC reciprocal"]
    assert source["defining_component"] == "AB=CD x1"
    assert source["selection_method"] == "abcd_equivalent_plus_reciprocal_bc"
    assert source["source_membership_authority"] == "carney_vol1_vol3"
    assert source["selection_authority"] == "carney_equivalent_abcd_plus_reciprocal_bc_pair"
    assert "v1-perfect-abcd-nqh4-10m" in source["market_case_ids"]


def test_source_aligned_price_zone_contract_keeps_bc_layering_outside_static_prz() -> None:
    # The lower-level golden test validates the layer math. This contract test guards the
    # semantic boundary consumed by UI: BC layering must never be represented as Source PRZ.
    points = (
        HarmonicPoint("A", 0, 200.0),
        HarmonicPoint("B", 1, 100.0),
        HarmonicPoint("C", 2, 161.8),
    )
    projection = project_forming_abcd(points)
    assert projection is not None
    payload = SourceAlignedHarmonicService._prz_payload(projection.prz)
    names = payload["source_prz"]["component_names"]
    assert names == ["AB=CD x1", "BC reciprocal"]
    assert all("layer" not in name.lower() for name in names)
