from __future__ import annotations

from typing import Any

import pandas as pd

from htcn.app.source_clock_lifecycle_service import M3SourceClockHarmonicService
from htcn.harmonic.discovery import (
    DISCOVERY_SCALES,
    DiscoveryCandidate,
    discover_frame,
)
from htcn.harmonic.models import Pivot


class RecognitionDiscoveryService(M3SourceClockHarmonicService):
    """Product-only high-recall discovery wrapper around the frozen M3 service.

    The parent service remains the sole owner of canonical identity, Source Raw PRZ,
    Source Clock and M4-relevant methodology. This adapter only appends research
    discovery payloads after the authoritative analysis has completed.
    """

    def _discovery_payload(
        self,
        item: DiscoveryCandidate,
        dates: pd.Series,
        pivots_by_scale: dict[int, tuple[Pivot, ...]],
        pivot_consensus: dict,
    ) -> dict[str, Any]:
        return {
            "pattern_id": item.pattern_id,
            "schema": "XABCD",
            "direction": item.direction.value,
            "state": "forming",
            "channel": "discovery",
            "discovery_only": True,
            "geometry_score": item.geometry_score,
            "scale": item.scale,
            "conflict_key": list(item.conflict_key),
            "identity_conflicts": [f"discovery:{item.pattern_id}@S{item.scale}"],
            "is_primary_identity": True,
            "points": [self._point_payload(point, dates) for point in item.points],
            "pivot_support": self._pivot_support_payload(
                item.points,
                source_scale=item.scale,
                pivots_by_scale=pivots_by_scale,
                consensus=pivot_consensus,
            ),
            "prz": self._prz_payload(item.prz),
            "metrics": {
                "b_xa": item.b_xa,
                "c_ab": item.c_ab,
            },
            "source_tolerance_used": item.source_tolerance_used,
            "bars_since_c": item.bars_since_c,
            "frontier": False,
            "discovery": {
                "authoritative_identity": False,
                "path_kind": item.path_kind,
                "skipped_pivots": item.skipped_pivots,
                "known_from_bar": item.known_from_bar,
                "prz_status": item.prz_status,
                "first_prz_test_bar": item.first_prz_test_bar,
                "c_family_target": item.c_family_target,
                "c_family_relative_error": item.c_family_relative_error,
                "source_family_aligned": item.source_family_aligned,
                "distance_to_source_prz_xa": item.distance_to_source_prz_xa,
                "mutates_source_identity": False,
                "owns_lifecycle": False,
                "fabricates_d": False,
            },
        }

    def analyze(
        self,
        *args,
        max_discovery: int = 60,
        **kwargs,
    ) -> dict[str, Any]:
        analysis = super().analyze(*args, **kwargs)
        bars = analysis.get("bars") or []
        frame = pd.DataFrame(bars)
        if frame.empty:
            analysis["discovery"] = []
            analysis["discovery_scales"] = list(DISCOVERY_SCALES)
            analysis["discovery_pivot_counts"] = {}
            analysis["recognition_diagnostics"] = {
                "authoritative_completed": len(analysis.get("completed") or []),
                "authoritative_forming": len(analysis.get("forming") or []),
                "discovery_candidates": 0,
                "windows_considered": 0,
                "raw_candidates": 0,
                "deduped_candidates": 0,
            }
            return analysis

        discovery_scan = discover_frame(
            frame,
            scales=DISCOVERY_SCALES,
            max_candidates=max_discovery,
        )
        dates = pd.Series(frame["trade_date"])
        discovery_pivots = {
            int(scale): tuple(pivots)
            for scale, pivots in discovery_scan.pivots_by_scale.items()
        }

        authoritative_xabc = {
            (
                str(pattern["pattern_id"]),
                tuple(int(point["index"]) for point in pattern["points"][:4]),
            )
            for pattern in [
                *(analysis.get("completed") or []),
                *(analysis.get("forming") or []),
            ]
            if pattern.get("schema") == "XABCD"
            and len(pattern.get("points") or []) >= 4
        }

        discovery = [
            self._discovery_payload(
                item,
                dates,
                discovery_pivots,
                discovery_scan.pivot_consensus,
            )
            for item in discovery_scan.candidates
            if (item.pattern_id, item.conflict_key) not in authoritative_xabc
        ][:max_discovery]

        analysis["discovery"] = discovery
        analysis["discovery_scales"] = list(DISCOVERY_SCALES)
        analysis["discovery_pivot_counts"] = {
            str(scale): len(pivots)
            for scale, pivots in discovery_scan.pivots_by_scale.items()
        }
        analysis["recognition_diagnostics"] = {
            "authoritative_completed": len(analysis.get("completed") or []),
            "authoritative_forming": len(analysis.get("forming") or []),
            "discovery_candidates": len(discovery),
            **discovery_scan.diagnostics,
        }
        analysis["engine_note"] = (
            str(analysis.get("engine_note") or "")
            + " M9 post-release recognition repair：高召回 discovery 是独立产品层；"
            "它只从已确认 XABC 投影既有 Source PRZ，可持久保留并有限跳过次级摆动，"
            "但不虚构 D、不拥有 Source lifecycle、不写 M4 evidence，也不改变 canonical identity。"
        ).strip()
        return analysis
