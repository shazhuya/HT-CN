from __future__ import annotations

from htcn.app.portable_visual_semantics import build_pattern_visual_semantics
from htcn.app.portable_visual_workspace_v2 import (
    build_portable_visual_workspace_html_v2,
)


def _xabcd_pattern(*, forming: bool = False) -> dict:
    points = [
        {"label": "X", "index": 5, "price": 100.0},
        {"label": "A", "index": 10, "price": 120.0},
        {"label": "B", "index": 15, "price": 110.0},
        {"label": "C", "index": 20, "price": 116.0},
    ]
    if not forming:
        points.append({"label": "D", "index": 27, "price": 102.0})
    return {
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "state": "forming" if forming else "completed",
        "scale": 5,
        "identity_conflicts": ["bat@S5", "gartley@S5"],
        "points": points,
        "metrics": {
            "b_xa": 0.5,
            "c_ab": 0.6,
            **({} if forming else {
                "bc_projection": 2.0,
                "d_xa": 0.9,
                "cd_ab": 1.4,
            }),
        },
        "prz": {
            "components": [
                {
                    "name": "XA completion",
                    "price_low": 101.8,
                    "price_high": 102.2,
                    "ratio_low": 0.886,
                    "ratio_high": 0.886,
                },
                {
                    "name": "BC projection x2",
                    "price_low": 102.6,
                    "price_high": 102.6,
                    "ratio_low": 2.0,
                    "ratio_high": 2.0,
                },
                {
                    "name": "AB=CD x1.27",
                    "price_low": 103.3,
                    "price_high": 103.3,
                    "ratio_low": 1.27,
                    "ratio_high": 1.27,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 101.8,
                "price_high": 102.6,
                "status": "frozen",
                "component_names": ["XA completion", "BC projection x2"],
                "defining_component": "XA completion",
                "selection_method": "fixture",
            },
            "ideal_core": {
                "price_low": 102.0,
                "price_high": 103.0,
            },
            "component_envelope": {
                "price_low": 101.8,
                "price_high": 103.3,
            },
        },
        "source_lifecycle": {
            "state": "type_ii_retest_forming",
            "state_reason": "fixture",
            "clock_source": "source_terminal_price_bar",
            "signal_bar": 21,
            "source_prz_entry_bar": 24,
            "source_terminal_bar": 27,
            "execution_start_bar": 28,
            "type_i_t1_bar": 30,
            "type_i_t2_bar": None,
            "first_source_prz_exit_bar": 31,
            "type_ii_retest_entry_bar": 35,
            "type_ii_terminal_bar": None,
            "reversal_exit_after_type_ii_bar": None,
            "target_382": 108.0,
            "target_618": 112.0,
            "next_key_price": 101.8,
            "next_key_price_role": "source_prz_terminal_side",
            "retrospective_geometry_clock_used": False,
        },
    }


def test_visual_semantics_separates_topology_ratios_and_prz_layers() -> None:
    payload = build_pattern_visual_semantics(_xabcd_pattern())

    assert payload["topology"]["status"] == "complete"
    assert [row["name"] for row in payload["topology"]["legs"]] == [
        "XA",
        "AB",
        "BC",
        "CD",
    ]
    assert [row["label"] for row in payload["ratios"]] == [
        "B / XA",
        "C / AB",
        "CD / BC 投影",
        "D / XA",
        "CD / AB",
    ]
    assert [row["id"] for row in payload["prz"]["layers"]] == [
        "source_raw_prz",
        "ideal_core",
        "component_envelope",
    ]
    components = {
        row["name"]: row
        for row in payload["prz"]["components"]
    }
    assert components["XA completion"]["source_raw_prz_member"] is True
    assert components["AB=CD x1.27"]["source_raw_prz_member"] is False
    assert (
        components["AB=CD x1.27"]["semantic_role"]
        == "audit_measurement_not_raw_prz"
    )


def test_forming_xabcd_reports_missing_d_but_never_draws_future_leg() -> None:
    payload = build_pattern_visual_semantics(
        _xabcd_pattern(forming=True)
    )

    assert payload["topology"]["status"] == "forming_prefix"
    assert payload["topology"]["missing_future_labels"] == ["D"]
    assert payload["topology"]["future_nodes_drawn"] is False
    assert [row["name"] for row in payload["topology"]["legs"]] == [
        "XA",
        "AB",
        "BC",
    ]
    assert payload["invents_future_pattern_points"] is False


def test_shark_schema_stays_0xabc_and_never_invents_d() -> None:
    pattern = {
        "pattern_id": "shark",
        "schema": "0XABC",
        "direction": "bullish",
        "state": "forming",
        "scale": 8,
        "points": [
            {"label": "0", "index": 3, "price": 90.0},
            {"label": "X", "index": 8, "price": 105.0},
            {"label": "A", "index": 13, "price": 97.0},
            {"label": "B", "index": 19, "price": 110.0},
        ],
        "metrics": {
            "a_0x": 0.53,
            "b_xa": 1.625,
        },
        "prz": {
            "components": [
                {
                    "name": "0B completion",
                    "price_low": 94.0,
                    "price_high": 96.0,
                    "ratio_low": 0.886,
                    "ratio_high": 1.13,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 94.0,
                "price_high": 96.0,
                "component_names": ["0B completion"],
            },
        },
    }

    payload = build_pattern_visual_semantics(pattern)

    assert payload["topology"]["expected_labels"] == [
        "0",
        "X",
        "A",
        "B",
        "C",
    ]
    assert payload["topology"]["missing_future_labels"] == ["C"]
    assert "D" not in payload["topology"]["expected_labels"]
    assert payload["topology"]["future_nodes_drawn"] is False


def test_five_zero_618_component_is_execution_refinement_not_raw_prz() -> None:
    pattern = {
        "pattern_id": "five_zero",
        "schema": "FIVE_ZERO",
        "direction": "bullish",
        "state": "completed",
        "scale": 5,
        "points": [
            {"label": "X", "index": 1, "price": 100.0},
            {"label": "A", "index": 5, "price": 115.0},
            {"label": "B", "index": 9, "price": 90.0},
            {"label": "C", "index": 14, "price": 125.0},
            {"label": "D", "index": 20, "price": 106.0},
        ],
        "metrics": {
            "b_xa": 1.4,
            "c_ab": 1.8,
            "d_bc": 0.54,
            "cd_ab": 0.8,
        },
        "prz": {
            "components": [
                {
                    "name": "BC 50% structural completion",
                    "price_low": 107.5,
                    "price_high": 107.5,
                    "ratio_low": 0.5,
                    "ratio_high": 0.5,
                },
                {
                    "name": "Reciprocal AB=CD x1",
                    "price_low": 105.0,
                    "price_high": 105.0,
                    "ratio_low": 1.0,
                    "ratio_high": 1.0,
                },
                {
                    "name": "BC 61.8% V3 execution boundary",
                    "price_low": 103.37,
                    "price_high": 103.37,
                    "ratio_low": 0.618,
                    "ratio_high": 0.618,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 105.0,
                "price_high": 107.5,
                "component_names": [
                    "BC 50% structural completion",
                    "Reciprocal AB=CD x1",
                ],
            },
        },
        "source_contract": {
            "raw_prz_members": [
                "BC 50% structural completion",
                "Reciprocal AB=CD x1",
            ]
        },
        "v3_execution_refinement": {
            "price_618": 103.37,
            "raw_prz_membership": False,
        },
    }

    payload = build_pattern_visual_semantics(pattern)
    components = {
        row["name"]: row
        for row in payload["prz"]["components"]
    }

    assert payload["schema_specific"]["production_quarantine"] is True
    assert (
        components["BC 61.8% V3 execution boundary"][
            "execution_refinement_only"
        ]
        is True
    )
    assert (
        components["BC 61.8% V3 execution boundary"][
            "source_raw_prz_member"
        ]
        is False
    )


def test_lifecycle_events_are_source_clock_ordered() -> None:
    payload = build_pattern_visual_semantics(_xabcd_pattern())

    bars = [
        row["bar"]
        for row in payload["lifecycle"]["events"]
    ]
    labels = [
        row["label"]
        for row in payload["lifecycle"]["events"]
    ]

    assert bars == sorted(bars)
    assert "Source T-Bar" in labels
    assert "T+1" in labels
    assert "Type-II 再入 PRZ" in labels
    assert all(
        row["is_pattern_geometry"] is False
        for row in payload["lifecycle"]["price_guides"]
    )


def test_visual_workspace_v2_exposes_layer_controls_and_no_write_surface() -> None:
    pattern = _xabcd_pattern()
    visual = build_pattern_visual_semantics(pattern)
    key = "fixture-key"
    inspection = {
        "source": {"verification_status": "valid"},
        "summary": {
            "status": "complete_detail_transport",
            "trade_date": "2026-09-19",
            "queue_display_key_count": 1,
            "detail_display_key_count": 1,
            "error_display_key_count": 0,
            "detail_complete": True,
        },
        "portable_items": [
            {
                "display_key": key,
                "detail_available": True,
                "detail_error": None,
                "queue": {
                    "display_key": key,
                    "instrument_id": "SSE.688256",
                    "pattern_id": "bat",
                    "schema": "XABCD",
                    "scale": 5,
                    "action_state": "reaction_observation",
                    "lifecycle_state": "type_ii_retest_forming",
                    "current_position": "fixture",
                    "first_watch": "fixture",
                    "next_key_price": 101.8,
                    "next_key_price_role": "source_prz_terminal_side",
                },
            }
        ],
        "details_by_display_key": {
            key: {
                "bars": [
                    {
                        "index": index,
                        "trade_date": f"2026-09-{min(index + 1, 19):02d}",
                        "open": 105.0,
                        "high": 107.0,
                        "low": 103.0,
                        "close": 106.0,
                    }
                    for index in range(40)
                ],
                "pattern": pattern,
                "visual_semantics": visual,
            }
        },
    }

    html = build_portable_visual_workspace_html_v2(
        inspection
    )

    assert "Visual Semantics v2" in html
    assert "Source Raw PRZ" in html
    assert "Ideal Core" in html
    assert "全组件 Envelope" in html
    assert "PRZ 组件线" in html
    assert "同几何身份冲突" in html
    assert "不绘制" in html
    assert "不是预测腿" in html
    assert "fetch(" not in html
    assert "review-session/event" not in html
