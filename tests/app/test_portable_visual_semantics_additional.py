from __future__ import annotations

from htcn.app.handoff_v4_inspector import HandoffV4InspectorContract
from htcn.app.portable_visual_semantics import build_pattern_visual_semantics


def test_abcd_schema_has_independent_topology_and_ratio_vocabulary() -> None:
    pattern = {
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "state": "completed",
        "scale": 3,
        "points": [
            {"label": "A", "index": 2, "price": 120.0},
            {"label": "B", "index": 6, "price": 100.0},
            {"label": "C", "index": 11, "price": 112.0},
            {"label": "D", "index": 17, "price": 91.5},
        ],
        "metrics": {
            "c_ab": 0.6,
            "bc_projection": 1.708,
            "cd_ab": 1.025,
            "reciprocal_c_target": 0.618,
            "reciprocal_bc_target": 1.618,
        },
        "prz": {
            "components": [
                {
                    "name": "AB=CD x1",
                    "price_low": 92.0,
                    "price_high": 92.0,
                    "ratio_low": 1.0,
                    "ratio_high": 1.0,
                },
                {
                    "name": "BC reciprocal",
                    "price_low": 91.0,
                    "price_high": 91.0,
                    "ratio_low": 1.618,
                    "ratio_high": 1.618,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 91.0,
                "price_high": 92.0,
                "component_names": ["AB=CD x1", "BC reciprocal"],
            },
        },
    }

    payload = build_pattern_visual_semantics(pattern)

    assert payload["topology"]["expected_labels"] == ["A", "B", "C", "D"]
    assert [row["name"] for row in payload["topology"]["legs"]] == [
        "AB",
        "BC",
        "CD",
    ]
    assert [row["label"] for row in payload["ratios"]] == [
        "C / AB",
        "CD / BC",
        "CD / AB",
        "C reciprocal 目标",
        "BC reciprocal 目标",
    ]


def test_inspector_contract_versions_visual_semantics_without_changing_transport() -> None:
    contract = HandoffV4InspectorContract().as_payload()

    assert contract["version"] == 2
    assert contract["source_bundle_schema"] == 4
    assert contract["visual_semantics_version"] == 2
    assert contract["future_pattern_points_may_be_invented"] is False
    assert contract["requires_market_database"] is False
    assert contract["writes_m4_evidence"] is False
