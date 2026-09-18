from __future__ import annotations

from dataclasses import asdict, dataclass
from math import isclose
from typing import Any

from htcn.app.decision_narrative import build_decision_narrative


@dataclass(frozen=True, slots=True)
class ProductContractIssue:
    code: str
    scope: str
    detail: str


@dataclass(frozen=True, slots=True)
class ProductContractAudit:
    passed: bool
    pattern_count: int
    issue_count: int
    issues: tuple[ProductContractIssue, ...]

    def as_payload(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "pattern_count": self.pattern_count,
            "issue_count": self.issue_count,
            "issues": [asdict(item) for item in self.issues],
        }


def _pattern_scope(pattern: dict[str, Any], index: int) -> str:
    points = pattern.get("points") or []
    tail = points[-1].get("index") if points else "na"
    return (
        f"pattern[{index}]:{pattern.get('state')}:{pattern.get('pattern_id')}"
        f":S{pattern.get('scale')}:{tail}"
    )


def _same_price(left: object, right: object) -> bool:
    if left is None or right is None:
        return left is right
    try:
        return isclose(float(left), float(right), rel_tol=1e-10, abs_tol=1e-10)
    except (TypeError, ValueError):
        return False


def audit_product_payload(analysis: dict[str, Any]) -> ProductContractAudit:
    issues: list[ProductContractIssue] = []
    patterns = [*(analysis.get("completed") or []), *(analysis.get("forming") or [])]
    top_execution = analysis.get("a_share_execution_context")
    integrity = analysis.get("context_integrity")
    contract = analysis.get("source_lifecycle_contract") or {}

    required_contract = {
        "canonical_clock": "source_terminal_price_bar",
        "geometry_terminal_promotes_live_state": False,
        "market_context_owns_lifecycle": False,
        "sector_context_owns_lifecycle": False,
        "concept_context_owns_lifecycle": False,
        "decision_narrative_is_trade_instruction": False,
        "mutates_harmonic_identity": False,
        "mutates_source_raw_prz": False,
        "no_backdating": True,
    }
    for key, expected in required_contract.items():
        actual = contract.get(key)
        if actual != expected:
            issues.append(ProductContractIssue(
                "contract_boundary_mismatch",
                "analysis.source_lifecycle_contract",
                f"{key} expected {expected!r}, got {actual!r}",
            ))

    integrity_layers = {
        str(item.get("layer")): str(item.get("state"))
        for item in ((integrity or {}).get("layers") or [])
    }
    expected_caution_prefixes = {
        f"{layer}:{state}"
        for layer, state in integrity_layers.items()
        if state != "current"
    }

    for index, pattern in enumerate(patterns):
        scope = _pattern_scope(pattern, index)
        lifecycle = pattern.get("source_lifecycle")
        narrative = pattern.get("decision_narrative")
        copied_execution = pattern.get("a_share_execution_context")

        if not isinstance(lifecycle, dict):
            issues.append(ProductContractIssue(
                "missing_source_lifecycle", scope,
                "pattern does not expose canonical source_lifecycle",
            ))
            continue
        if not isinstance(narrative, dict):
            issues.append(ProductContractIssue(
                "missing_decision_narrative", scope,
                "pattern does not expose Phase-4 decision_narrative",
            ))
            continue

        lifecycle_state = str(lifecycle.get("state"))
        if narrative.get("lifecycle_state") != lifecycle_state:
            issues.append(ProductContractIssue(
                "narrative_lifecycle_mismatch", scope,
                f"narrative={narrative.get('lifecycle_state')!r}, lifecycle={lifecycle_state!r}",
            ))

        rebuilt = build_decision_narrative(
            source_lifecycle=lifecycle,
            context_integrity=integrity,
        ).as_payload()
        if narrative.get("action_state") != rebuilt["action_state"]:
            issues.append(ProductContractIssue(
                "action_state_mismatch", scope,
                f"expected {rebuilt['action_state']!r}, got {narrative.get('action_state')!r}",
            ))

        if narrative.get("next_key_price_role") != lifecycle.get("next_key_price_role"):
            issues.append(ProductContractIssue(
                "next_key_price_role_mismatch", scope,
                (
                    f"narrative={narrative.get('next_key_price_role')!r}, "
                    f"lifecycle={lifecycle.get('next_key_price_role')!r}"
                ),
            ))
        if not _same_price(
            narrative.get("next_key_price"),
            lifecycle.get("next_key_price"),
        ):
            issues.append(ProductContractIssue(
                "next_key_price_mismatch", scope,
                (
                    f"narrative={narrative.get('next_key_price')!r}, "
                    f"lifecycle={lifecycle.get('next_key_price')!r}"
                ),
            ))

        if top_execution is not None and copied_execution != top_execution:
            issues.append(ProductContractIssue(
                "execution_context_copy_mismatch", scope,
                "pattern execution context differs from top-level execution context",
            ))

        actual_cautions = {
            str(item).split(" — ", 1)[0]
            for item in (narrative.get("context_cautions") or [])
        }
        if actual_cautions != expected_caution_prefixes:
            issues.append(ProductContractIssue(
                "context_caution_mismatch", scope,
                f"expected={sorted(expected_caution_prefixes)}, got={sorted(actual_cautions)}",
            ))

        for flag in (
            "is_trade_instruction",
            "uses_score",
            "mutates_harmonic_identity",
            "mutates_source_raw_prz",
            "owns_lifecycle",
        ):
            if narrative.get(flag) is not False:
                issues.append(ProductContractIssue(
                    "narrative_boundary_violation", scope,
                    f"{flag} must be false",
                ))

        if pattern.get("schema") == "FIVE_ZERO":
            reason = str(lifecycle.get("state_reason") or "")
            if lifecycle_state != "source_clock_unavailable" or "quarantine" not in reason:
                issues.append(ProductContractIssue(
                    "five_zero_quarantine_violation", scope,
                    "5-0 must stay source_clock_unavailable with quarantine reason",
                ))

    return ProductContractAudit(
        passed=not issues,
        pattern_count=len(patterns),
        issue_count=len(issues),
        issues=tuple(issues),
    )


def assert_product_payload(analysis: dict[str, Any]) -> None:
    audit = audit_product_payload(analysis)
    if audit.passed:
        return
    lines = [
        f"{item.code} [{item.scope}] {item.detail}"
        for item in audit.issues
    ]
    raise AssertionError(
        "M3 product contract failed:\n" + "\n".join(lines)
    )
