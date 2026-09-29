from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from decimal import Decimal
from itertools import pairwise
from pathlib import Path

from htcn.harmonic.confluence_audit import audit_projection_confluence
from htcn.harmonic.models import HarmonicPoint
from htcn.harmonic.prz import build_xabcd_prz
from htcn.harmonic.rules import CARNEY_RULES
from htcn.harmonic.source_completion import (
    SourceCompletionEvent,
    SourceCompletionScan,
    SourceProjection,
    _projection_state,
    event_sourced_hierarchical_xabc_projections,
    scan_source_completion_events,
)
from htcn.research.snapshot_cache import load_research_snapshot

ROOT = Path(__file__).resolve().parents[1]


def audit() -> dict:
    selection_path = ROOT / "research/recognition-gate4c-case-selection-v1.json"
    selection = json.loads(selection_path.read_text())
    cases = []
    completion_events = {}
    detector_states = {}
    birth_prefixes = {}
    for case in selection["cases"]:
        snapshot, reason = load_research_snapshot(
            ROOT / "artifacts/ci-research/data",
            instrument_id=case["instrument_id"], requested_start="2016-01-01",
            requested_end="2026-09-15", max_bars=3000, price_mode="qfq",
        )
        if snapshot is None:
            raise ValueError(f"{case['case_id']}: {reason}")
        frame = snapshot.frame.reset_index(drop=True)
        bullish = case["direction"] == "bullish"
        nodes = []
        for j, (label, index) in enumerate(zip("XABC", case["source_nodes"])):
            row = frame.iloc[index]
            date = row["trade_date"].date().isoformat()
            if date != case["source_dates"][j]:
                raise ValueError("case and snapshot date identity mismatch")
            field = "low" if (j % 2 == 0) == bullish else "high"
            nodes.append({"label": label, "index": index, "date": date,
                          "price": float(row[field]), "price_field": field})
        points = tuple(HarmonicPoint(label=n["label"], index=n["index"], price=n["price"])
                       for n in nodes)
        prz = build_xabcd_prz(CARNEY_RULES[case["pattern_id"]], points)
        # Independent arithmetic: no production projector, selector or ratio helper.
        x, a, b, c = [Decimal(str(n["price"])) for n in nodes]
        xa, ab, bc = abs(a - x), abs(b - a), abs(c - b)
        sign = Decimal(-1 if bullish else 1)
        measured = []
        for component in prz.components:
            ratio = Decimal(str(component.ratio_low))
            if component.ratio_low != component.ratio_high:
                raise ValueError("audit requires exact component ratios")
            if component.name == "XA completion":
                price = a + sign * ratio * xa
            elif component.name.startswith("BC projection"):
                price = c + sign * ratio * bc
            elif component.name.startswith("AB=CD"):
                price = c + sign * ratio * ab
            else:
                raise ValueError("unknown measurement")
            error = abs(float(price) - component.midpoint)
            if error > 1e-8:
                raise ValueError("independent measurement mismatch")
            measured.append({"name": component.name, "ratio": float(ratio),
                             "price": float(price), "selected": component.name in
                             prz.source_prz_component_names, "absolute_error": error})
        selected = [m["price"] for m in measured if m["selected"]]
        if abs(min(selected) - prz.source_prz_low) > 1e-8:
            raise ValueError("lower boundary mismatch")
        if abs(max(selected) - prz.source_prz_high) > 1e-8:
            raise ValueError("upper boundary mismatch")
        defining = next(m["price"] for m in measured if m["name"] == "XA completion")
        required_bc = abs(float(c) - defining) / float(bc)
        projection = SourceProjection(
            pattern_id=case["pattern_id"], direction=prz.direction, points=points,
            known_at=case["known_at"], prz=prz, scales=(),
            min_skipped_pivots=case["min_skipped_pivots"],
        )
        state = _projection_state(frame, projection, lifetime_bars=180)
        series = (case["instrument_id"], snapshot.sha256)
        if series not in detector_states:
            actual = scan_source_completion_events(frame)
            detector_states[series] = {item.projection.key: item for item in actual.states}
        recovered = detector_states[series].get(projection.key)
        for cutoff in (case["known_at"] - 1, case["known_at"]):
            prefix_key = (*series, cutoff)
            if prefix_key not in birth_prefixes:
                birth_prefixes[prefix_key] = {
                    item.key: item for item in event_sourced_hierarchical_xabc_projections(
                        frame.iloc[:cutoff + 1])}
        at_birth = birth_prefixes[(*series, case["known_at"])].get(projection.key)
        before_birth = birth_prefixes[(*series, case["known_at"] - 1)].get(projection.key)
        replay_checks = {
            "nodes_recovered": recovered is not None,
            "absent_before_birth": before_birth is None,
            "present_at_birth": at_birth is not None,
            "birth_matches": recovered is not None and
                             recovered.projection.known_at == case["known_at"],
            "node_prices_match": recovered is not None and
                                 recovered.projection.points == points,
            "prz_matches": recovered is not None and recovered.projection.prz == prz,
            "state_matches": recovered is not None and recovered.state == state.state,
            "close_bar_matches": recovered is not None and recovered.closed_bar == state.closed_bar,
            "birth_evidence_not_backfilled": recovered is not None and at_birth is not None and
                (recovered.projection.known_at, recovered.projection.scales,
                 recovered.projection.min_skipped_pivots) ==
                (at_birth.known_at, at_birth.scales, at_birth.min_skipped_pivots),
        }

        if state.state == "completed":
            completion_events.setdefault(case["instrument_id"], []).append(
                SourceCompletionEvent(projection, state.audit))
        selected_bc = next(m["price"] for m in measured if m["selected"] and
                           m["name"].startswith("BC projection"))
        touched = {}
        for measurement in (m for m in measured if m["selected"]):
            hits = [i for i in range(case["known_at"] + 1, case["terminal_bar"] + 1)
                    if float(frame.iloc[i]["low"]) <= measurement["price"] <=
                    float(frame.iloc[i]["high"])]
            touched[measurement["name"]] = hits[0] if hits else None
        # Independent raw-bar envelope evidence: the graph checks confirmed
        # pivots, while an omitted/unconfirmed extreme can still cross a leg.
        # These are diagnostics, not a new Source identity or rejection rule.
        leg_checks = []
        for left, right in pairwise(points):
            interior = frame.iloc[left.index + 1:right.index]
            lower, upper = sorted((left.price, right.price))
            below = [int(i) for i in range(left.index + 1, right.index)
                     if float(frame.iloc[i]["low"]) < lower]
            above = [int(i) for i in range(left.index + 1, right.index)
                     if float(frame.iloc[i]["high"]) > upper]
            leg_checks.append({
                "leg": left.label + right.label,
                "endpoint_bounds": [lower, upper],
                "interior_low": None if interior.empty else float(interior["low"].min()),
                "interior_high": None if interior.empty else float(interior["high"].max()),
                "below_endpoint_bars": below, "above_endpoint_bars": above,
                "raw_envelope_contained": not below and not above,
            })
        cases.append({
            **case, "snapshot_sha256": snapshot.sha256, "nodes": nodes,
            "raw_leg_envelope_checks": leg_checks,
            "detector_replay_checks": replay_checks,
            "detector_replay_passed": all(replay_checks.values()),
            "b_xa": float(ab / xa), "c_ab": float(bc / ab),
            "components": measured, "source_prz": [prz.source_prz_low, prz.source_prz_high],
            "independent_width_xa": (max(selected) - min(selected)) / float(xa),
            "primary_xa_bc_separation_xa": abs(defining - selected_bc) / float(xa),
            "required_bc_ratio_at_exact_xa": required_bc,
            "selected_measurement_first_touch": touched,
            "all_selected_measurements_observed_by_old_terminal": all(
                index is not None for index in touched.values()),
            "v2_policy_state": state.state, "v2_closed_bar": state.closed_bar,
            "v2_reason": state.reason,
            "math_ruling": "valid_independent_measurements",
            "qualification_screen": asdict(audit_projection_confluence(
                case["pattern_id"], points, prz)),
            "validated_identity": False,
            "semantic_ruling": "uncertain_requires_confluence_qualification",
            "rationale": "Arithmetic agreement is not semantic acceptance. Inspect XA/BC "
                         "separation and observed measurement coverage; no width cutoff invented.",
            "source_refs": list(prz.source_prz_source_refs),
            "observation_rows": [
                {"index": i, "date": frame.iloc[i]["trade_date"].date().isoformat(),
                 **{k: float(frame.iloc[i][k]) for k in ["open", "high", "low", "close"]}}
                for i in range(case["source_nodes"][0], case["terminal_bar"] + 1)
            ],
        })
    groups = []
    for instrument_id, events in sorted(completion_events.items()):
        scan = SourceCompletionScan((), (), tuple(events), 0, 0, 0)
        for group in scan.completion_groups:
            groups.append({"instrument_id": instrument_id, "key": group.key,
                           "interpretation_count": len(group.interpretations),
                           "source_nodes": [e.source_nodes for e in group.interpretations],
                           "validated_identity": False})
    return {"schema": 3, "completion_groups": groups,
            "detector_replay_passed": all(c["detector_replay_passed"] for c in cases),
            "completion_interpretation_count": sum(len(v) for v in completion_events.values()),
            "completion_observation_group_count": len(groups),
            "grouping_scope": "Same-series direction/ABC/Terminal grouping; not independent trades or verified identities", "selection_sha256": hashlib.sha256(selection_path.read_bytes()).hexdigest(),
            "source_artifact": selection["source_artifact"],
            "scope": "11 preselected challenge cases, not precision/recall estimation",
            "case_count": len(cases), "cases": cases}


if __name__ == "__main__":
    report = audit()
    path = ROOT / "artifacts/reports/m9-recognition-gate4c-case-audit.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"case_count": report["case_count"], "report": str(path),
                      "detector_replay_passed": report["detector_replay_passed"]}))
    if not report["detector_replay_passed"]:
        raise SystemExit("Raw-OHLC detector replay disagrees with frozen cases; inspect report")
