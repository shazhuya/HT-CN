from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from htcn.app.portable_visual_semantics import build_pattern_visual_semantics
from htcn.app.portable_visual_workspace_v2 import (
    build_portable_visual_workspace_html_v2,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HTML = ROOT / "apps" / "web" / "public" / "portable-visual-fixture.html"
DEFAULT_JSON = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase18-portable-visual-fixture.json"
)


def _bars() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for index in range(52):
        base = 105.0 + ((index % 7) - 3) * 1.25
        rows.append(
            {
                "index": index,
                "trade_date": f"2026-09-{min(index + 1, 30):02d}",
                "open": base - 0.35,
                "high": base + 1.15,
                "low": base - 1.05,
                "close": base + 0.25,
                "volume": 1000.0 + index * 17.0,
            }
        )
    return rows


def _lifecycle(
    *,
    state: str,
    source_low: float,
    source_high: float,
    terminal_bar: int | None,
    execution_start_bar: int | None,
    next_key_price: float,
    next_key_price_role: str,
) -> dict[str, Any]:
    return {
        "state": state,
        "state_reason": f"Phase18 fixture: {state}",
        "clock_source": "source_terminal_price_bar",
        "current_bar": 51,
        "signal_bar": 20,
        "source_prz_entry_bar": 25,
        "source_terminal_bar": terminal_bar,
        "execution_start_bar": execution_start_bar,
        "bars_since_terminal": (
            None if terminal_bar is None else 51 - terminal_bar
        ),
        "type_i_t1_bar": 31 if terminal_bar is not None else None,
        "type_i_t2_bar": 35 if terminal_bar is not None else None,
        "first_source_prz_exit_bar": 33 if terminal_bar is not None else None,
        "type_ii_retest_entry_bar": 39 if terminal_bar is not None else None,
        "type_ii_terminal_bar": 42 if terminal_bar is not None else None,
        "reversal_exit_after_type_ii_bar": 45 if terminal_bar is not None else None,
        "source_prz_low": source_low,
        "source_prz_high": source_high,
        "pez_low": source_low - 0.25 if terminal_bar is not None else None,
        "pez_high": source_high + 0.15 if terminal_bar is not None else None,
        "target_382": 110.8 if terminal_bar is not None else None,
        "target_618": 114.2 if terminal_bar is not None else None,
        "next_key_price": next_key_price,
        "next_key_price_role": next_key_price_role,
        "strict_type_ii_full_retest": True,
        "retrospective_geometry_clock_used": False,
    }


def _xabcd_completed() -> dict[str, Any]:
    return {
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "state": "completed",
        "scale": 5,
        "identity_conflicts": ["bat@S5", "gartley@S5"],
        "is_primary_identity": True,
        "points": [
            {"label": "X", "index": 4, "price": 100.0, "trade_date": "2026-09-05"},
            {"label": "A", "index": 10, "price": 120.0, "trade_date": "2026-09-11"},
            {"label": "B", "index": 16, "price": 109.8, "trade_date": "2026-09-17"},
            {"label": "C", "index": 22, "price": 116.2, "trade_date": "2026-09-23"},
            {"label": "D", "index": 28, "price": 102.1, "trade_date": "2026-09-29"},
        ],
        "metrics": {
            "b_xa": 0.51,
            "c_ab": 0.627,
            "bc_projection": 2.203,
            "d_xa": 0.895,
            "cd_ab": 1.382,
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
                    "name": "BC projection x2.24",
                    "price_low": 102.45,
                    "price_high": 102.45,
                    "ratio_low": 2.24,
                    "ratio_high": 2.24,
                },
                {
                    "name": "AB=CD x1.27",
                    "price_low": 103.25,
                    "price_high": 103.25,
                    "ratio_low": 1.27,
                    "ratio_high": 1.27,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 101.8,
                "price_high": 102.45,
                "status": "frozen",
                "component_names": ["XA completion", "BC projection x2.24"],
                "defining_component": "XA completion",
                "selection_method": "phase18_fixture",
            },
            "ideal_core": {
                "price_low": 102.0,
                "price_high": 103.0,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": 101.8,
                "price_high": 103.25,
                "status": "audit_envelope_not_source_prz",
            },
        },
        "source_lifecycle": _lifecycle(
            state="reversal_evidence",
            source_low=101.8,
            source_high=102.45,
            terminal_bar=28,
            execution_start_bar=29,
            next_key_price=114.2,
            next_key_price_role="type_i_61_8_target",
        ),
        "decision_narrative": {"action_state": "execution_evaluation"},
    }


def _xabcd_forming() -> dict[str, Any]:
    return {
        "pattern_id": "crab",
        "schema": "XABCD",
        "direction": "bearish",
        "state": "forming",
        "scale": 8,
        "identity_conflicts": ["crab@S8"],
        "is_primary_identity": True,
        "points": [
            {"label": "X", "index": 6, "price": 118.0, "trade_date": "2026-09-07"},
            {"label": "A", "index": 12, "price": 96.0, "trade_date": "2026-09-13"},
            {"label": "B", "index": 18, "price": 108.4, "trade_date": "2026-09-19"},
            {"label": "C", "index": 24, "price": 100.8, "trade_date": "2026-09-25"},
        ],
        "metrics": {
            "b_xa": 0.564,
            "c_ab": 0.613,
        },
        "prz": {
            "components": [
                {
                    "name": "XA completion",
                    "price_low": 130.0,
                    "price_high": 131.0,
                    "ratio_low": 1.618,
                    "ratio_high": 1.618,
                },
                {
                    "name": "BC projection x2.618",
                    "price_low": 129.4,
                    "price_high": 129.4,
                    "ratio_low": 2.618,
                    "ratio_high": 2.618,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 129.4,
                "price_high": 131.0,
                "status": "frozen",
                "component_names": ["XA completion", "BC projection x2.618"],
                "defining_component": "XA completion",
                "selection_method": "phase18_fixture",
            },
            "ideal_core": {
                "price_low": 129.8,
                "price_high": 130.6,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": 129.4,
                "price_high": 131.0,
                "status": "audit_envelope_not_source_prz",
            },
        },
        "source_lifecycle": _lifecycle(
            state="approaching_source_prz",
            source_low=129.4,
            source_high=131.0,
            terminal_bar=None,
            execution_start_bar=None,
            next_key_price=129.4,
            next_key_price_role="source_prz_entry_edge",
        ),
        "decision_narrative": {"action_state": "waiting"},
    }


def _abcd_completed() -> dict[str, Any]:
    return {
        "pattern_id": "abcd",
        "schema": "ABCD",
        "direction": "bullish",
        "state": "completed",
        "scale": 3,
        "identity_conflicts": ["abcd@S3"],
        "is_primary_identity": True,
        "points": [
            {"label": "A", "index": 5, "price": 121.0, "trade_date": "2026-09-06"},
            {"label": "B", "index": 11, "price": 101.0, "trade_date": "2026-09-12"},
            {"label": "C", "index": 17, "price": 113.2, "trade_date": "2026-09-18"},
            {"label": "D", "index": 25, "price": 92.8, "trade_date": "2026-09-26"},
        ],
        "metrics": {
            "c_ab": 0.61,
            "bc_projection": 1.672,
            "cd_ab": 1.02,
            "reciprocal_c_target": 0.618,
            "reciprocal_bc_target": 1.618,
        },
        "prz": {
            "components": [
                {
                    "name": "AB=CD x1",
                    "price_low": 93.2,
                    "price_high": 93.2,
                    "ratio_low": 1.0,
                    "ratio_high": 1.0,
                },
                {
                    "name": "BC reciprocal",
                    "price_low": 92.5,
                    "price_high": 92.5,
                    "ratio_low": 1.618,
                    "ratio_high": 1.618,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 92.5,
                "price_high": 93.2,
                "status": "frozen",
                "component_names": ["AB=CD x1", "BC reciprocal"],
                "defining_component": "AB=CD x1",
                "selection_method": "equivalent_abcd_plus_reciprocal_bc",
            },
            "ideal_core": {
                "price_low": 92.6,
                "price_high": 93.0,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": 92.5,
                "price_high": 93.2,
                "status": "audit_envelope_not_source_prz",
            },
        },
        "source_lifecycle": _lifecycle(
            state="type_i_confirmed",
            source_low=92.5,
            source_high=93.2,
            terminal_bar=25,
            execution_start_bar=26,
            next_key_price=114.2,
            next_key_price_role="type_i_61_8_target",
        ),
        "decision_narrative": {"action_state": "reaction_observation"},
    }


def _shark_completed() -> dict[str, Any]:
    return {
        "pattern_id": "shark",
        "schema": "0XABC",
        "direction": "bullish",
        "state": "completed",
        "scale": 8,
        "identity_conflicts": ["shark@S8"],
        "is_primary_identity": True,
        "points": [
            {"label": "0", "index": 3, "price": 88.0, "trade_date": "2026-09-04"},
            {"label": "X", "index": 9, "price": 105.0, "trade_date": "2026-09-10"},
            {"label": "A", "index": 15, "price": 96.5, "trade_date": "2026-09-16"},
            {"label": "B", "index": 21, "price": 110.0, "trade_date": "2026-09-22"},
            {"label": "C", "index": 29, "price": 94.7, "trade_date": "2026-09-30"},
        ],
        "metrics": {
            "a_0x": 0.5,
            "b_xa": 1.588,
            "c_ab": 1.133,
            "c_0b": 0.91,
        },
        "prz": {
            "components": [
                {
                    "name": "0B completion corridor",
                    "price_low": 94.1,
                    "price_high": 96.0,
                    "ratio_low": 0.886,
                    "ratio_high": 1.13,
                },
                {
                    "name": "AB impulse corridor",
                    "price_low": 93.8,
                    "price_high": 95.4,
                    "ratio_low": 1.618,
                    "ratio_high": 2.24,
                },
            ],
            "source_prz": {
                "available": True,
                "price_low": 94.1,
                "price_high": 95.4,
                "status": "frozen",
                "component_names": [
                    "0B completion corridor",
                    "AB impulse corridor",
                ],
                "defining_component": "0B completion corridor",
                "selection_method": "corridor_overlap",
            },
            "ideal_core": {
                "price_low": 94.2,
                "price_high": 95.2,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": 93.8,
                "price_high": 96.0,
                "status": "audit_envelope_not_source_prz",
            },
        },
        "reaction_targets": {
            "target_50": 102.35,
            "target_618": 104.15,
            "reciprocal_abcd": 108.2,
            "initial_target": 102.35,
            "initial_target_basis": "50_percent",
            "management_rule": "first_of_50_percent_or_reciprocal_abcd",
        },
        "source_lifecycle": _lifecycle(
            state="type_i_confirmed",
            source_low=94.1,
            source_high=95.4,
            terminal_bar=29,
            execution_start_bar=30,
            next_key_price=104.15,
            next_key_price_role="type_i_61_8_target",
        ),
        "decision_narrative": {"action_state": "reaction_observation"},
    }


def _five_zero_completed() -> dict[str, Any]:
    return {
        "pattern_id": "five_zero",
        "schema": "FIVE_ZERO",
        "direction": "bullish",
        "state": "completed",
        "scale": 5,
        "identity_conflicts": ["five_zero@S5"],
        "is_primary_identity": True,
        "points": [
            {"label": "X", "index": 4, "price": 100.0, "trade_date": "2026-09-05"},
            {"label": "A", "index": 10, "price": 115.0, "trade_date": "2026-09-11"},
            {"label": "B", "index": 16, "price": 90.0, "trade_date": "2026-09-17"},
            {"label": "C", "index": 23, "price": 125.0, "trade_date": "2026-09-24"},
            {"label": "D", "index": 30, "price": 106.0, "trade_date": "2026-09-30"},
        ],
        "metrics": {
            "b_xa": 1.667,
            "c_ab": 1.4,
            "d_bc": 0.543,
            "cd_ab": 0.76,
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
                    "price_low": 100.0,
                    "price_high": 100.0,
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
                "price_low": 100.0,
                "price_high": 107.5,
                "status": "frozen",
                "component_names": [
                    "BC 50% structural completion",
                    "Reciprocal AB=CD x1",
                ],
                "defining_component": "BC 50% structural completion",
                "selection_method": "volume2_50_bc_plus_reciprocal_abcd",
            },
            "ideal_core": {
                "price_low": 102.0,
                "price_high": 106.0,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": 100.0,
                "price_high": 107.5,
                "status": "audit_envelope_not_source_prz",
            },
        },
        "source_contract": {
            "raw_prz_members": [
                "BC 50% structural completion",
                "Reciprocal AB=CD x1",
            ],
        },
        "v3_execution_refinement": {
            "price_618": 103.37,
            "raw_prz_membership": False,
            "identity_membership": False,
        },
        "source_lifecycle": {
            "state": "source_clock_unavailable",
            "state_reason": "five_zero_production_quarantine",
            "clock_source": "source_terminal_price_bar",
            "current_bar": 51,
            "signal_bar": None,
            "source_prz_entry_bar": None,
            "source_terminal_bar": None,
            "execution_start_bar": None,
            "bars_since_terminal": None,
            "type_i_t1_bar": None,
            "type_i_t2_bar": None,
            "first_source_prz_exit_bar": None,
            "type_ii_retest_entry_bar": None,
            "type_ii_terminal_bar": None,
            "reversal_exit_after_type_ii_bar": None,
            "source_prz_low": None,
            "source_prz_high": None,
            "pez_low": None,
            "pez_high": None,
            "target_382": None,
            "target_618": None,
            "next_key_price": None,
            "next_key_price_role": None,
            "strict_type_ii_full_retest": True,
            "retrospective_geometry_clock_used": False,
        },
        "decision_narrative": {"action_state": "evidence_insufficient"},
    }


def _queue_item(
    *,
    display_key: str,
    instrument_id: str,
    pattern: dict[str, Any],
    current_position: str,
) -> dict[str, Any]:
    life = pattern.get("source_lifecycle") or {}
    return {
        "display_key": display_key,
        "instrument_id": instrument_id,
        "pattern_id": pattern["pattern_id"],
        "schema": pattern["schema"],
        "direction": pattern["direction"],
        "scale": pattern["scale"],
        "pattern_state": pattern["state"],
        "action_state": (pattern.get("decision_narrative") or {}).get(
            "action_state"
        ),
        "lifecycle_state": life.get("state"),
        "current_position": current_position,
        "first_watch": "Phase18 browser fixture first watch",
        "next_watch": "Phase18 browser fixture next watch",
        "upgrade_blocker": "Phase18 browser fixture blocker",
        "next_key_price": life.get("next_key_price"),
        "next_key_price_role": life.get("next_key_price_role"),
        "context_cautions": [],
    }


def build_fixture() -> dict[str, Any]:
    cases = [
        (
            "phase18-xabcd-complete",
            "SSE.600001",
            _xabcd_completed(),
            "XABCD 已完成",
        ),
        (
            "phase18-xabcd-forming",
            "SSE.600002",
            _xabcd_forming(),
            "XABCD 形成中",
        ),
        (
            "phase18-abcd-complete",
            "SSE.600003",
            _abcd_completed(),
            "AB=CD 已完成",
        ),
        (
            "phase18-shark-complete",
            "SSE.600004",
            _shark_completed(),
            "Shark 已完成",
        ),
        (
            "phase18-five-zero",
            "SSE.600005",
            _five_zero_completed(),
            "5-0 quarantine",
        ),
    ]

    portable_items: list[dict[str, Any]] = []
    details: dict[str, dict[str, Any]] = {}
    bars = _bars()
    for display_key, instrument_id, pattern, current_position in cases:
        queue = _queue_item(
            display_key=display_key,
            instrument_id=instrument_id,
            pattern=pattern,
            current_position=current_position,
        )
        portable_items.append(
            {
                "display_key": display_key,
                "instrument_id": instrument_id,
                "queue": queue,
                "detail_available": True,
                "detail_error": None,
            }
        )
        details[display_key] = {
            "display_key": display_key,
            "instrument_id": instrument_id,
            "trade_date": "2026-09-19",
            "price_mode": "qfq",
            "warning": None,
            "bars": bars,
            "pattern": pattern,
            "visual_semantics": build_pattern_visual_semantics(pattern),
        }

    return {
        "schema_version": 2,
        "contract": {
            "version": 2,
            "semantics": "phase18_browser_fixture",
            "source_bundle_schema": 4,
            "visual_semantics_version": 2,
            "requires_market_database": False,
            "writes_m4_evidence": False,
            "is_trade_instruction": False,
        },
        "source": {
            "bundle_path": "phase18-fixture",
            "verification_status": "valid",
            "bundle_schema_version": 4,
            "bundle_file_count": 7,
        },
        "summary": {
            "status": "complete_detail_transport",
            "trade_date": "2026-09-19",
            "queue_display_key_count": len(cases),
            "detail_display_key_count": len(cases),
            "error_display_key_count": 0,
            "detail_complete": True,
        },
        "portable_items": portable_items,
        "details_by_display_key": details,
        "detail_errors": [],
        "phase18_fixture": True,
    }


def main() -> int:
    fixture = build_fixture()
    DEFAULT_HTML.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_JSON.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_HTML.write_text(
        build_portable_visual_workspace_html_v2(fixture),
        encoding="utf-8",
    )
    DEFAULT_JSON.write_text(
        json.dumps(
            fixture,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
            allow_nan=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": "ready",
                "html": str(DEFAULT_HTML),
                "json": str(DEFAULT_JSON),
                "case_count": len(fixture["portable_items"]),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
