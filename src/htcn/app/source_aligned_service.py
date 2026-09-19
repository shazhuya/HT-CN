from __future__ import annotations

from dataclasses import asdict
from typing import Any

import pandas as pd

from htcn.app.harmonic_service import LocalHarmonicService
from htcn.harmonic.abcd_source import abcd_bc_layering_example, with_abcd_source_prz
from htcn.harmonic.execution import observe_source_execution
from htcn.harmonic.models import PatternDirection
from htcn.harmonic.prz import PotentialReversalZone, PRZComponent
from htcn.harmonic.rsi_bamm import RSIBammDirection, scan_rsi_bamm_frame
from htcn.harmonic.rsi_bamm_confluence import (
    confirm_rsi_bamm_with_source_execution,
    observe_source_execution_for_match,
)
from htcn.harmonic.rsi_bamm_lifecycle import audit_rsi_bamm_at_source_clock
from htcn.harmonic.source_prz_evidence import source_prz_evidence


class SourceAlignedHarmonicService(LocalHarmonicService):
    """Compatibility-preserving API adapter for the source-fidelity contract."""

    @staticmethod
    def _prz_payload(prz: PotentialReversalZone) -> dict[str, Any]:
        effective = with_abcd_source_prz(prz) if prz.pattern_id == "abcd" else prz
        legacy = LocalHarmonicService._prz_payload(prz)
        component_low = float(prz.component_envelope_low)
        component_high = float(prz.component_envelope_high)
        ideal_low = float(prz.ideal_core_low)
        ideal_high = float(prz.ideal_core_high)
        source_available = bool(effective.has_source_prz)
        source_low = float(effective.source_prz_low) if effective.source_prz_low is not None else None
        source_high = float(effective.source_prz_high) if effective.source_prz_high is not None else None
        evidence = source_prz_evidence(prz.pattern_id)
        abcd_evidence_level = (
            "source_specification_plus_market_examples_membership_only"
            if prz.pattern_id == "abcd"
            else "unregistered"
        )

        return {
            **legacy,
            "semantics_version": 3,
            "legacy_price_semantics": "ideal_core",
            "ideal_core": {
                "price_low": ideal_low,
                "price_high": ideal_high,
                "width": ideal_high - ideal_low,
                "status": "htcn_convergence_selection",
            },
            "component_envelope": {
                "price_low": component_low,
                "price_high": component_high,
                "width": component_high - component_low,
                "status": "audit_envelope_not_source_prz",
            },
            "source_prz": {
                "available": source_available,
                "price_low": source_low,
                "price_high": source_high,
                "width": (
                    source_high - source_low
                    if source_low is not None and source_high is not None
                    else None
                ),
                "status": effective.source_prz_status,
                "component_names": list(effective.source_prz_component_names),
                "defining_component": effective.source_prz_defining_component,
                "selection_method": effective.source_prz_selection_method,
                "source_refs": list(effective.source_prz_source_refs),
                "source_note": effective.source_prz_note or None,
                "unresolved_reason": effective.source_prz_reason,
                "profile_version": 2,
                "evidence_level": (
                    evidence.evidence_level if evidence else abcd_evidence_level
                ),
                "source_membership_authority": (
                    evidence.source_membership_authority
                    if evidence
                    else ("Carney Vol1/Vol3" if prz.pattern_id == "abcd" else None)
                ),
                "selection_authority": (
                    evidence.selection_authority
                    if evidence
                    else (
                        "Carney-defined equivalent AB=CD + reciprocal BC pair"
                        if prz.pattern_id == "abcd"
                        else None
                    )
                ),
                "market_case_ids": list(evidence.market_case_ids) if evidence else [],
                "known_source_tensions": list(evidence.known_tensions) if evidence else [],
                "coordinate_regression_status": (
                    evidence.coordinate_regression_status if evidence else "pending_book_coordinates"
                ),
            },
        }

    @staticmethod
    def _rsi_bamm_confluence_payload(item: Any, frame: pd.DataFrame) -> dict[str, Any]:
        """Expose source-clock-confirmed BAMM without mutating harmonic identity.

        Phase 4 reconstructs the observable Source Terminal Price Bar from the pre-terminal
        projection and binds BAMM to that clock. Historical D/C remains diagnostic geometry only.
        Evidence is timestamped no earlier than both the T-Bar and BAMM sequence completion.
        """
        required = {"close", "low", "high"}
        if not required.issubset(frame.columns):
            return {
                "status": "unavailable_missing_ohlc",
                "sequence_count": 0,
                "source_confirmed_count": 0,
                "available_from_bar": None,
                "available_at_source_terminal": False,
                "mutates_harmonic_identity": False,
            }

        direction = RSIBammDirection(str(item.direction.value))
        sequences = scan_rsi_bamm_frame(frame, direction=direction)
        audit = observe_source_execution_for_match(frame, item)
        confluences = [
            confirm_rsi_bamm_with_source_execution(sequence, item, audit)
            for sequence in sequences
        ]
        confirmed = [row for row in confluences if row.source_confirmed]
        geometry_terminal_bar = int(item.points[-1].index)
        source_terminal_bar = None if audit is None else audit.terminal_bar
        source_terminal_price = None if audit is None else audit.terminal_price

        if not confirmed:
            return {
                "status": "no_source_confirmed_confluence",
                "sequence_count": len(sequences),
                "source_confirmed_count": 0,
                "available_from_bar": None,
                "available_at_source_terminal": False,
                "geometry_terminal_bar": geometry_terminal_bar,
                "source_terminal_bar": source_terminal_bar,
                "source_terminal_price": source_terminal_price,
                "source_execution_state": None if audit is None else audit.state,
                "candidate_statuses": sorted({row.status for row in confluences}),
                "terminal_source": "source_terminal_price_bar",
                "mutates_harmonic_identity": False,
            }

        latest = max(confirmed, key=lambda row: int(row.sequence.completion_bar))
        sequence = latest.sequence
        assert latest.terminal_bar is not None
        terminal_bar = int(latest.terminal_bar)
        available_from = max(terminal_bar, int(sequence.completion_bar))
        available_at_source_terminal = available_from <= terminal_bar
        return {
            "status": latest.status,
            "sequence_count": len(sequences),
            "source_confirmed_count": len(confirmed),
            "available_from_bar": available_from,
            "available_at_source_terminal": available_at_source_terminal,
            # Compatibility alias. Its semantic source is now explicitly the observable T-Bar.
            "available_at_pattern_terminal": available_at_source_terminal,
            "geometry_terminal_bar": geometry_terminal_bar,
            "source_terminal_bar": terminal_bar,
            "source_terminal_price": latest.terminal_price,
            "bamm_completion_bar": int(sequence.completion_bar),
            "profile": sequence.profile.value,
            "relation": sequence.relation.value,
            "confirmation_extension_ratio": float(sequence.confirmation_extension_ratio),
            "confirmation_projection_price": sequence.confirmation_projection_price,
            "price_projection_tested": bool(sequence.price_projection_tested),
            "pattern_precedence_used": bool(
                latest.confirmation is not None and latest.confirmation.pattern_precedence_used
            ),
            "terminal_source": latest.terminal_source,
            "terminal_tests_source_prz": latest.terminal_tests_source_prz,
            "terminal_in_source_prz": latest.terminal_in_source_prz,
            "mutates_harmonic_identity": False,
        }

    def _completed_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._completed_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        payload["rsi_bamm_evidence"] = self._rsi_bamm_confluence_payload(item, frame)
        return payload

    def _abcd_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._abcd_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        evaluation = item.evaluation
        layer = abcd_bc_layering_example(
            item.points,
            reciprocal_bc_target=float(evaluation.reciprocal_bc_target),
        )
        payload["execution_tolerance"] = {
            **asdict(layer),
            "raw_prz_membership": False,
            "identity_membership": False,
        }
        payload["rsi_bamm_evidence"] = self._rsi_bamm_confluence_payload(item, frame)
        return payload

    def _abcd_forming_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._abcd_forming_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        projection = item.projection
        layer = abcd_bc_layering_example(
            item.points,
            reciprocal_bc_target=float(projection.reciprocal_bc_target),
        )
        payload["execution_tolerance"] = {
            **asdict(layer),
            "raw_prz_membership": False,
            "identity_membership": False,
        }
        return payload

    def _shark_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._shark_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        evaluation = item.evaluation
        completion_index = int(item.points[-1].index)
        targets = payload["reaction_targets"]
        targets.update(
            {
                "initial_target": float(evaluation.initial_target),
                "initial_target_basis": evaluation.initial_target_basis,
                "bars_to_initial_target": self._bars_to_target(
                    frame,
                    completion_index=completion_index,
                    target=float(evaluation.initial_target),
                    direction=item.direction,
                ),
                "management_rule": "first_of_50_percent_or_reciprocal_abcd",
                "source_note": (
                    "Shark 为反应型结构。Volume Three 的初始获利目标取进入 5-0 PRZ 时"
                    "50% BC 回撤与 Reciprocal AB=CD 两项中从 C 点先到达者；61.8% 保留为"
                    "后续 5-0/风险边界测量，不能机械当作 Shark 第一目标。"
                ),
            }
        )
        payload["rsi_bamm_evidence"] = self._rsi_bamm_confluence_payload(item, frame)
        return payload

    def _five_zero_payload(self, *args, **kwargs) -> dict[str, Any]:
        payload = super()._five_zero_payload(*args, **kwargs)
        item = args[0] if args else kwargs["item"]
        frame = args[1] if len(args) > 1 else kwargs["frame"]
        evaluation = item.evaluation
        contract = evaluation.source_contract
        payload["prz"] = self._prz_payload(evaluation.prz)
        payload["source_contract"] = {
            "status": "structural_source_prz_frozen_execution_label_conflict_quarantined",
            "price_50_bc": float(contract.price_50_bc),
            "reciprocal_abcd_price": float(contract.reciprocal_abcd_price),
            "reciprocal_relation": contract.reciprocal_relation,
            "source_prz_low": float(contract.source_prz_low),
            "source_prz_high": float(contract.source_prz_high),
            "raw_prz_members": list(evaluation.prz.source_prz_component_names),
            "source_raw_prz_test": bool(evaluation.source_raw_prz_test),
            "completion_class": evaluation.completion_class,
        }
        payload["v3_execution_refinement"] = asdict(contract.execution_refinement)
        payload["compatibility_diagnostics"] = {
            "legacy_reciprocal_inside_50_618_band": bool(
                evaluation.reciprocal_inside_execution_band
            ),
            "identity_gate": False,
            "note": "该旧 band 指标仅保留兼容审计，M2.29 起不得参与 5-0 pass/fail。",
        }
        payload["rsi_bamm_evidence"] = self._rsi_bamm_confluence_payload(item, frame)
        return payload

    @staticmethod
    def _rebuild_prz_from_payload(pattern: dict[str, Any]) -> PotentialReversalZone:
        raw = pattern["prz"]
        source = raw.get("source_prz") or {}
        components = tuple(PRZComponent(**component) for component in raw.get("components") or [])
        if not components:
            raise ValueError("forming pattern PRZ payload has no auditable components")
        return PotentialReversalZone(
            pattern_id=str(pattern["pattern_id"]),
            direction=PatternDirection(str(pattern["direction"])),
            components=components,
            source_prz_low=(
                float(source["price_low"])
                if source.get("available") is True and source.get("price_low") is not None
                else None
            ),
            source_prz_high=(
                float(source["price_high"])
                if source.get("available") is True and source.get("price_high") is not None
                else None
            ),
            source_prz_component_names=tuple(source.get("component_names") or ()),
            source_prz_defining_component=source.get("defining_component"),
            source_prz_selection_method=source.get("selection_method"),
            source_prz_source_refs=tuple(source.get("source_refs") or ()),
            source_prz_note=str(source.get("source_note") or ""),
            source_prz_reason=source.get("unresolved_reason"),
        )

    @classmethod
    def _execution_clock_from_forming_payload(
        cls,
        pattern: dict[str, Any],
        frame: pd.DataFrame,
    ) -> dict[str, Any] | None:
        schema = str(pattern.get("schema"))
        if schema not in {"XABCD", "ABCD", "0XABC"}:
            return None
        points = list(pattern.get("points") or [])
        if not points:
            return None
        frontier = points[-1]
        scale = int(pattern["scale"])
        signal_bar = int(frontier["index"]) + scale
        if signal_bar < 0 or signal_bar >= len(frame):
            return {
                "state": "frontier_confirmation_outside_returned_window",
                "signal_bar": signal_bar,
                "signal_clock_basis": "last_frontier_pivot_confirmed_at=index+scale",
                "confirmation_lag_bars": scale,
                "pez": {"available": False, "price_low": None, "price_high": None},
                "rsi_bamm_evidence": {
                    "status": "source_clock_unavailable",
                    "source_confirmed": False,
                    "mutates_harmonic_identity": False,
                },
            }

        reaction_anchor_label = "B" if schema == "0XABC" else "A"
        reaction_anchor = next(
            (point for point in points if point.get("label") == reaction_anchor_label),
            None,
        )
        if reaction_anchor is None:
            return None
        prz = cls._rebuild_prz_from_payload(pattern)
        audit = observe_source_execution(
            frame,
            signal_bar=signal_bar,
            direction=PatternDirection(str(pattern["direction"])),
            prz=prz,
            reaction_anchor_price=float(reaction_anchor["price"]),
            observation_end_bar=len(frame) - 1,
        )
        clock = audit.as_payload()
        clock.update(
            {
                "signal_clock_basis": "last_frontier_pivot_confirmed_at=index+scale",
                "frontier_pivot_index": int(frontier["index"]),
                "confirmation_lag_bars": scale,
                "reaction_anchor_label": reaction_anchor_label,
                "reaction_anchor_price": float(reaction_anchor["price"]),
                "retrospective_d_clock_used": False,
                "pez": {
                    "available": audit.pez_low is not None and audit.pez_high is not None,
                    "price_low": audit.pez_low,
                    "price_high": audit.pez_high,
                    "status": (
                        "terminal_integrated_execution_zone"
                        if audit.pez_low is not None and audit.pez_high is not None
                        else "not_available_before_terminal"
                    ),
                },
            }
        )
        if schema == "0XABC":
            a_point = next((point for point in points if point.get("label") == "A"), None)
            b_point = next((point for point in points if point.get("label") == "B"), None)
            clock["type_i_target_semantics"] = (
                "generic_type_i_reaction_confirmation_only_not_shark_management_target"
            )
            if audit.terminal_price is None or a_point is None or b_point is None:
                clock["shark_management"] = {
                    "status": "waiting_for_source_terminal_bar",
                    "initial_target": None,
                    "initial_target_basis": None,
                    "target_50_bc": None,
                    "target_618_bc": None,
                    "reciprocal_abcd": None,
                    "source_note": (
                        "Shark 专用管理在 Source T-Bar 后冻结：50% BC 与 Reciprocal AB=CD "
                        "二者从 C/T-Bar 先到者为 initial target；61.8% BC 为后续 5-0/管理参考。"
                    ),
                }
            else:
                terminal = float(audit.terminal_price)
                a_price = float(a_point["price"])
                b_price = float(b_point["price"])
                sign = 1.0 if PatternDirection(str(pattern["direction"])) is PatternDirection.BULLISH else -1.0
                bc_span = abs(b_price - terminal)
                ab_span = abs(a_price - b_price)
                target_50 = terminal + sign * 0.50 * bc_span
                target_618 = terminal + sign * 0.618 * bc_span
                reciprocal = terminal + sign * ab_span
                d50 = abs(target_50 - terminal)
                drec = abs(reciprocal - terminal)
                eps = 1e-12 * max(1.0, d50, drec)
                if abs(d50 - drec) <= eps:
                    initial_target = target_50
                    initial_basis = "50_percent_and_reciprocal_abcd_tie"
                elif d50 < drec:
                    initial_target = target_50
                    initial_basis = "50_percent"
                else:
                    initial_target = reciprocal
                    initial_basis = "reciprocal_abcd"
                clock["shark_management"] = {
                    "status": "source_terminal_observed",
                    "initial_target": float(initial_target),
                    "initial_target_basis": initial_basis,
                    "target_50_bc": float(target_50),
                    "target_618_bc": float(target_618),
                    "reciprocal_abcd": float(reciprocal),
                    "source_note": (
                        "Shark 专用管理与通用 Type-I 状态分离：initial target 取 50% BC "
                        "与 Reciprocal AB=CD 先到者；61.8% BC 保留为后续 5-0/管理参考。"
                    ),
                }

        if audit.terminal_bar is None:
            clock["rsi_bamm_evidence"] = {
                "status": "waiting_for_source_terminal_bar",
                "source_confirmed": False,
                "mutates_harmonic_identity": False,
            }
        elif {"close", "low", "high"}.issubset(frame.columns):
            clock["rsi_bamm_evidence"] = audit_rsi_bamm_at_source_clock(
                frame,
                direction=str(pattern["direction"]),
                source_clock_bar=int(audit.terminal_bar),
                observed_through_bar=len(frame) - 1,
            ).as_payload()
        else:
            clock["rsi_bamm_evidence"] = {
                "status": "unavailable_missing_ohlc",
                "source_confirmed": False,
                "mutates_harmonic_identity": False,
            }
        return clock

    def analyze(self, *args, **kwargs) -> dict[str, Any]:
        analysis = super().analyze(*args, **kwargs)
        frame = pd.DataFrame(analysis.get("bars") or [])
        for pattern in analysis.get("forming") or []:
            clock = self._execution_clock_from_forming_payload(pattern, frame)
            if clock is not None:
                pattern["execution_clock"] = clock
            elif pattern.get("schema") == "0XABC":
                pattern["execution_clock_policy"] = "shark_uses_pattern_specific_5_0_target_contract"
            elif pattern.get("schema") == "FIVE_ZERO":
                pattern["execution_clock_policy"] = (
                    "structural_source_prz_frozen_v3_execution_label_conflict_quarantined"
                )
        analysis["price_zone_contract"] = {
            "version": 3,
            "source_prz_profile_version": 2,
            "static_layers": ["ideal_core", "component_envelope", "source_prz"],
            "dynamic_layer": "execution_clock.pez",
            "execution_only_layers": [
                "ABCD.execution_tolerance",
                "FIVE_ZERO.v3_execution_refinement",
            ],
            "fail_closed_without_source_prz": True,
            "legacy_price_low_high_mean": "ideal_core",
            "source_membership_authority": "Carney source families per pattern",
            "source_selection_authority": "HT-CN operational convergence only where Carney leaves multiple source-valid complements",
        }
        analysis["rsi_bamm_contract"] = {
            "version": 2,
            "role": "confirmation_execution_evidence_only",
            "completed_match_channel": "completed[].rsi_bamm_evidence",
            "completed_match_clock": "source_terminal_price_bar_reconstructed_from_pre_terminal_projection",
            "source_clock_channel": "forming[].execution_clock.rsi_bamm_evidence",
            "geometry_terminal_is_execution_terminal": False,
            "no_backdating": True,
            "pez_overspill_allowed": True,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
        }
        analysis["engine_note"] = (
            str(analysis.get("engine_note") or "")
            + " M2.28 已把 standalone AB=CD 的等距完成价 + reciprocal BC 解冻为 Source Raw PRZ；"
            "Volume Three BC layering 单列为 execution tolerance，绝不进入 identity 或 Raw PRZ。"
            " M2.29 已冻结 5-0 的 Volume Two Structural Raw PRZ=50% BC + Reciprocal AB=CD；"
            "Volume Three 61.8 仅作为 execution refinement/stop reference，并显式保留 XA/AB 标签冲突。"
            "5-0 仍处于 production quarantine；Alternate Bat 仍 source-conflict fail closed。"
            " M2.31 将 RSI BAMM 作为独立 confirmation/execution evidence channel 接入；"
            "completed confluence 绑定 Source Terminal Price Bar，不再把历史 D/C 冒充 T-Bar；"
            "任何 BAMM 证据不得改写 harmonic identity 或 Source Raw PRZ，且完成时间不得回填。"
        ).strip()
        return analysis
