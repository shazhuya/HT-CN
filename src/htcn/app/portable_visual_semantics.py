from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

VISUAL_SEMANTICS_VERSION = 2


@dataclass(frozen=True, slots=True)
class PortableVisualSemanticsContract:
    version: int = VISUAL_SEMANTICS_VERSION
    semantics: str = "presentation_only_from_transported_pattern_payload"
    mutates_harmonic_identity: bool = False
    mutates_source_raw_prz: bool = False
    mutates_source_lifecycle: bool = False
    invents_future_pattern_points: bool = False
    projected_geometry_is_pattern_identity: bool = False
    predictive_score_used: bool = False
    historical_outcome_used_for_ranking: bool = False
    alpha_inference_allowed: bool = False
    is_trade_instruction: bool = False

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


_SCHEMA_NODES: dict[str, tuple[str, ...]] = {
    "XABCD": ("X", "A", "B", "C", "D"),
    "ABCD": ("A", "B", "C", "D"),
    "0XABC": ("0", "X", "A", "B", "C"),
    "FIVE_ZERO": ("X", "A", "B", "C", "D"),
}

_SCHEMA_NAMES: dict[str, str] = {
    "XABCD": "标准 XABCD",
    "ABCD": "独立 AB=CD",
    "0XABC": "Shark 0-X-A-B-C",
    "FIVE_ZERO": "5-0 X-A-B-C-D",
}

_RATIO_DEFINITIONS: dict[str, tuple[tuple[str, str], ...]] = {
    "XABCD": (
        ("b_xa", "B / XA"),
        ("c_ab", "C / AB"),
        ("bc_projection", "CD / BC 投影"),
        ("d_xa", "D / XA"),
        ("cd_ab", "CD / AB"),
    ),
    "ABCD": (
        ("c_ab", "C / AB"),
        ("bc_projection", "CD / BC"),
        ("cd_ab", "CD / AB"),
        ("reciprocal_c_target", "C reciprocal 目标"),
        ("reciprocal_bc_target", "BC reciprocal 目标"),
    ),
    "0XABC": (
        ("a_0x", "A / 0X"),
        ("b_xa", "B / XA"),
        ("c_ab", "C / AB"),
        ("c_0b", "C / 0B"),
    ),
    "FIVE_ZERO": (
        ("b_xa", "B / XA"),
        ("c_ab", "C / AB"),
        ("d_bc", "D / BC"),
        ("cd_ab", "CD / AB"),
    ),
}

_EVENT_DEFINITIONS: tuple[tuple[str, str, str], ...] = (
    ("signal_bar", "投影可观察", "source_clock"),
    ("source_prz_entry_bar", "首次进入 Source PRZ", "source_clock"),
    ("source_terminal_bar", "Source T-Bar", "terminal"),
    ("execution_start_bar", "T+1", "terminal"),
    ("type_i_t1_bar", "Type-I 38.2%", "type_i"),
    ("type_i_t2_bar", "Type-I 61.8%", "type_i"),
    ("first_source_prz_exit_bar", "首次反转方向离开 PRZ", "type_ii"),
    ("type_ii_retest_entry_bar", "Type-II 再入 PRZ", "type_ii"),
    ("type_ii_terminal_bar", "Type-II T-Bar", "type_ii"),
    ("reversal_exit_after_type_ii_bar", "Type-II 后反转方向离开", "type_ii"),
)


def _number(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if number != number:
        return None
    return number


def _int_or_none(value: object) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _range_payload(raw: object) -> dict[str, float] | None:
    if not isinstance(raw, dict):
        return None
    low = _number(raw.get("price_low"))
    high = _number(raw.get("price_high"))
    if low is None or high is None:
        return None
    return {
        "price_low": min(low, high),
        "price_high": max(low, high),
    }


def _topology(pattern: dict[str, Any]) -> dict[str, Any]:
    schema = str(pattern.get("schema") or "")
    expected = _SCHEMA_NODES.get(schema, ())
    points = [
        dict(point)
        for point in (pattern.get("points") or [])
        if isinstance(point, dict)
    ]
    labels = tuple(str(point.get("label") or "") for point in points)

    if not expected:
        status = "unsupported_schema"
    elif labels == expected:
        status = "complete"
    elif labels == expected[: len(labels)] and len(labels) < len(expected):
        status = "forming_prefix"
    else:
        status = "invalid_non_prefix"

    legs: list[dict[str, Any]] = []
    for ordinal, (left, right) in enumerate(zip(points, points[1:]), start=1):
        left_label = str(left.get("label") or "")
        right_label = str(right.get("label") or "")
        left_price = _number(left.get("price"))
        right_price = _number(right.get("price"))
        legs.append(
            {
                "ordinal": ordinal,
                "name": f"{left_label}{right_label}",
                "from_label": left_label,
                "to_label": right_label,
                "from_index": _int_or_none(left.get("index")),
                "to_index": _int_or_none(right.get("index")),
                "from_price": left_price,
                "to_price": right_price,
                "price_length": (
                    None
                    if left_price is None or right_price is None
                    else abs(right_price - left_price)
                ),
                "observed_geometry": True,
                "line_style": "solid",
            }
        )

    missing = list(expected[len(labels) :]) if status == "forming_prefix" else []
    return {
        "schema": schema,
        "schema_name": _SCHEMA_NAMES.get(schema, schema or "未知 schema"),
        "expected_labels": list(expected),
        "observed_labels": list(labels),
        "status": status,
        "observed_node_count": len(labels),
        "expected_node_count": len(expected),
        "missing_future_labels": missing,
        "future_nodes_drawn": False,
        "legs": legs,
    }


def _ratios(pattern: dict[str, Any]) -> list[dict[str, Any]]:
    schema = str(pattern.get("schema") or "")
    metrics = pattern.get("metrics")
    if not isinstance(metrics, dict):
        return []

    checks = {
        str(row.get("name") or ""): row
        for row in (pattern.get("checks") or [])
        if isinstance(row, dict)
    }
    rows: list[dict[str, Any]] = []
    for key, label in _RATIO_DEFINITIONS.get(schema, ()):
        value = _number(metrics.get(key))
        if value is None:
            continue
        check = checks.get(key)
        rows.append(
            {
                "key": key,
                "label": label,
                "value": value,
                "kind": "ratio",
                "source_check_passed": (
                    None if not isinstance(check, dict) else check.get("passed")
                ),
                "source_check_target": (
                    None if not isinstance(check, dict) else check.get("target")
                ),
                "presentation_only": True,
            }
        )
    return rows


def _prz_semantics(pattern: dict[str, Any]) -> dict[str, Any]:
    raw = pattern.get("prz")
    if not isinstance(raw, dict):
        return {
            "source_prz_available": False,
            "layers": [],
            "components": [],
        }

    source = raw.get("source_prz")
    source = source if isinstance(source, dict) else {}
    source_range = _range_payload(source)
    source_names = {
        str(value)
        for value in (source.get("component_names") or [])
        if value
    }
    layers: list[dict[str, Any]] = []

    if source.get("available") is True and source_range is not None:
        layers.append(
            {
                "id": "source_raw_prz",
                "label": "Source Raw PRZ",
                "semantic_role": "source_defined_reversal_zone",
                "visual_priority": 0,
                "line_style": "solid",
                "fill_style": "primary_zone",
                **source_range,
            }
        )

    ideal = _range_payload(raw.get("ideal_core"))
    if ideal is not None:
        layers.append(
            {
                "id": "ideal_core",
                "label": "HT-CN Ideal Core",
                "semantic_role": "engineering_convergence_selection_not_source_prz",
                "visual_priority": 1,
                "line_style": "dashed",
                "fill_style": "engineering_zone",
                **ideal,
            }
        )

    envelope = _range_payload(raw.get("component_envelope"))
    if envelope is None:
        low = _number(raw.get("component_price_low"))
        high = _number(raw.get("component_price_high"))
        if low is not None and high is not None:
            envelope = {
                "price_low": min(low, high),
                "price_high": max(low, high),
            }
    if envelope is not None:
        layers.append(
            {
                "id": "component_envelope",
                "label": "全组件审计 Envelope",
                "semantic_role": "audit_envelope_not_source_prz",
                "visual_priority": 2,
                "line_style": "dotted",
                "fill_style": "audit_zone",
                **envelope,
            }
        )

    components: list[dict[str, Any]] = []
    for raw_component in raw.get("components") or []:
        if not isinstance(raw_component, dict):
            continue
        name = str(raw_component.get("name") or "")
        low = _number(raw_component.get("price_low"))
        high = _number(raw_component.get("price_high"))
        if low is None or high is None:
            continue
        source_member = name in source_names
        execution_refinement = (
            str(pattern.get("schema") or "") == "FIVE_ZERO"
            and "61.8" in name
            and not source_member
        )
        components.append(
            {
                "name": name,
                "price_low": min(low, high),
                "price_high": max(low, high),
                "ratio_low": _number(raw_component.get("ratio_low")),
                "ratio_high": _number(raw_component.get("ratio_high")),
                "source_raw_prz_member": source_member,
                "execution_refinement_only": execution_refinement,
                "semantic_role": (
                    "source_raw_prz_member"
                    if source_member
                    else (
                        "execution_refinement_not_raw_prz"
                        if execution_refinement
                        else "audit_measurement_not_raw_prz"
                    )
                ),
                "line_style": "solid" if source_member else "dotted",
            }
        )

    return {
        "source_prz_available": (
            source.get("available") is True and source_range is not None
        ),
        "source_prz_status": source.get("status"),
        "source_prz_component_names": sorted(source_names),
        "source_prz_defining_component": source.get("defining_component"),
        "source_prz_selection_method": source.get("selection_method"),
        "layers": sorted(layers, key=lambda row: int(row["visual_priority"])),
        "components": components,
    }


def _lifecycle(pattern: dict[str, Any]) -> dict[str, Any]:
    life = pattern.get("source_lifecycle")
    if not isinstance(life, dict):
        return {
            "available": False,
            "state": None,
            "events": [],
            "price_guides": [],
        }

    events: list[dict[str, Any]] = []
    for field, label, group in _EVENT_DEFINITIONS:
        bar = _int_or_none(life.get(field))
        if bar is None:
            continue
        events.append(
            {
                "field": field,
                "label": label,
                "bar": bar,
                "group": group,
                "line_style": "dashed",
            }
        )
    events.sort(key=lambda row: (int(row["bar"]), str(row["field"])))

    guides: list[dict[str, Any]] = []
    for field, label, role in (
        ("target_382", "Type-I 38.2%", "reaction_target"),
        ("target_618", "Type-I 61.8%", "reaction_target"),
        ("next_key_price", "下一关键价", "next_key_guide"),
    ):
        price = _number(life.get(field))
        if price is None:
            continue
        guides.append(
            {
                "field": field,
                "label": label,
                "price": price,
                "role": role,
                "line_style": "dashed",
                "is_pattern_geometry": False,
            }
        )

    return {
        "available": True,
        "state": life.get("state"),
        "state_reason": life.get("state_reason"),
        "clock_source": life.get("clock_source"),
        "events": events,
        "price_guides": guides,
        "retrospective_geometry_clock_used": life.get(
            "retrospective_geometry_clock_used"
        ),
    }


def _schema_specific(pattern: dict[str, Any]) -> dict[str, Any]:
    schema = str(pattern.get("schema") or "")
    output: dict[str, Any] = {
        "schema": schema,
        "production_quarantine": schema == "FIVE_ZERO",
    }

    if schema == "0XABC":
        targets = pattern.get("reaction_targets")
        targets = targets if isinstance(targets, dict) else {}
        output["shark_management"] = {
            "initial_target": _number(targets.get("initial_target")),
            "initial_target_basis": targets.get("initial_target_basis"),
            "target_50": _number(targets.get("target_50")),
            "target_618": _number(targets.get("target_618")),
            "reciprocal_abcd": _number(targets.get("reciprocal_abcd")),
            "management_rule": targets.get("management_rule"),
            "reaction_structure_not_xabcd_d": True,
        }

    if schema == "FIVE_ZERO":
        output["five_zero_boundary"] = {
            "raw_prz_members": list(
                (pattern.get("source_contract") or {}).get("raw_prz_members") or []
            )
            if isinstance(pattern.get("source_contract"), dict)
            else [],
            "v3_execution_refinement": (
                dict(pattern.get("v3_execution_refinement") or {})
                if isinstance(pattern.get("v3_execution_refinement"), dict)
                else None
            ),
            "visual_warning": (
                "5-0 仍处 production quarantine；61.8 仅显示为执行 refinement，"
                "不得画成 Source Raw PRZ 成员。"
            ),
        }

    return output


def build_pattern_visual_semantics(
    pattern: dict[str, Any],
) -> dict[str, Any]:
    """Derive deterministic presentation semantics from one transported pattern.

    The function does not project new harmonic points. A forming schema may report the
    labels that are still missing, but those labels never become drawable geometry.
    """

    topology = _topology(pattern)
    warnings: list[str] = []
    if topology["status"] == "invalid_non_prefix":
        warnings.append(
            "节点标签不符合该 schema 的前缀拓扑；图形层应 fail closed，不补点。"
        )
    if topology["status"] == "unsupported_schema":
        warnings.append("未知 schema；只允许展示原始 transport 信息。")
    if topology["missing_future_labels"]:
        warnings.append(
            "形成中结构存在尚未发生的节点；这些节点只列为缺失，不绘制未来腿。"
        )

    prz = _prz_semantics(pattern)
    if not prz["source_prz_available"]:
        warnings.append(
            "Source Raw PRZ 不可用；Ideal Core/Envelope 只能作为工程或审计层展示。"
        )

    schema_specific = _schema_specific(pattern)
    if schema_specific.get("production_quarantine"):
        warnings.append("5-0 production quarantine：视觉展示不代表生产解封。")

    return {
        "schema_version": VISUAL_SEMANTICS_VERSION,
        "contract": PortableVisualSemanticsContract().as_payload(),
        "pattern_id": pattern.get("pattern_id"),
        "schema": pattern.get("schema"),
        "direction": pattern.get("direction"),
        "state": pattern.get("state"),
        "scale": pattern.get("scale"),
        "topology": topology,
        "ratios": _ratios(pattern),
        "prz": prz,
        "lifecycle": _lifecycle(pattern),
        "schema_specific": schema_specific,
        "identity_conflicts": list(pattern.get("identity_conflicts") or []),
        "warnings": warnings,
        "presentation_only": True,
        "authoritative_evidence": False,
        "writes_m4_evidence": False,
        "mutates_harmonic_identity": False,
        "mutates_source_raw_prz": False,
        "mutates_source_lifecycle": False,
        "invents_future_pattern_points": False,
        "is_trade_instruction": False,
    }
