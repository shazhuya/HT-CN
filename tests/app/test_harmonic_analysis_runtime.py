from __future__ import annotations

from htcn.app.harmonic_analysis_runtime import (
    build_analysis_runtime_provenance,
    empty_harmonic_analysis_runtime_status,
    evaluate_harmonic_analysis_schedule,
    execute_harmonic_analysis_cycle,
    read_harmonic_analysis_runtime_status,
    write_harmonic_analysis_runtime_status,
)
from htcn.app.operator_input_identity import (
    AnalysisCodeIdentity,
    DataInputIdentity,
    OperatorCacheInputIdentity,
)


def _identity(fingerprint: str = "input-a") -> OperatorCacheInputIdentity:
    return OperatorCacheInputIdentity(
        contract_version=1,
        fingerprint=fingerprint,
        data=DataInputIdentity(
            contract_version=1,
            fingerprint=f"data-{fingerprint}",
            component_count=2,
        ),
        analysis_code=AnalysisCodeIdentity(
            contract_version=1,
            fingerprint=f"code-{fingerprint}",
            component_count=3,
        ),
    )


def _queue(*, failed: int = 0, stable: bool = True) -> dict:
    analyzed = 2 - failed
    return {
        "schema_version": 2,
        "contract": {
            "predictive_score_used": False,
            "historical_outcome_used": False,
            "alpha_inference_allowed": False,
            "is_trade_instruction": False,
            "mutates_harmonic_identity": False,
            "mutates_source_raw_prz": False,
            "owns_lifecycle": False,
        },
        "as_of_trade_date": "2026-09-22",
        "observation_integrity": "single_as_of",
        "instrument_count": 2,
        "analyzed_instrument_count": analyzed,
        "failed_instrument_count": failed,
        "candidate_count": 3,
        "items": [],
        "errors": [],
        "product_cache": {
            "freshness": "current",
            "input_identity_stable_during_build": stable,
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "status": "rebuilt",
        },
    }


def test_schedule_is_idempotent_for_same_trade_date_and_input_identity() -> None:
    decision = evaluate_harmonic_analysis_schedule(
        target_trade_date="2026-09-22",
        input_identity_fingerprint="same",
        last_success_trade_date="2026-09-22",
        last_success_input_identity_fingerprint="same",
    )
    assert decision.due is False
    assert decision.reason == "already_current"


def test_schedule_runs_for_new_canonical_session() -> None:
    decision = evaluate_harmonic_analysis_schedule(
        target_trade_date="2026-09-22",
        input_identity_fingerprint="same",
        last_success_trade_date="2026-09-21",
        last_success_input_identity_fingerprint="same",
    )
    assert decision.due is True
    assert decision.reason == "new_canonical_trade_session"


def test_schedule_reruns_same_session_when_canonical_input_identity_changes() -> None:
    decision = evaluate_harmonic_analysis_schedule(
        target_trade_date="2026-09-22",
        input_identity_fingerprint="new",
        last_success_trade_date="2026-09-22",
        last_success_input_identity_fingerprint="old",
    )
    assert decision.due is True
    assert decision.reason == "canonical_input_changed"


def test_runtime_reuses_operator_snapshot_without_becoming_source_truth(tmp_path) -> None:
    calls: dict[str, object] = {}

    def snapshot_builder(service, instrument_ids, **kwargs):
        calls["service"] = service
        calls["instrument_ids"] = list(instrument_ids)
        calls["kwargs"] = kwargs
        return _queue()

    marker_service = object()
    payload = execute_harmonic_analysis_cycle(
        marker_service,
        ["SSE.1", "SZSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-22",
        input_identity=_identity(),
        bars=420,
        scales=(3, 5),
        max_workers=4,
        snapshot_builder=snapshot_builder,
    )

    assert payload["healthy"] is True
    assert payload["overall_status"] == "healthy"
    assert payload["failed_instrument_count"] == 0
    provenance = payload["provenance"]
    assert provenance["viewport_inputs_used"] is False
    assert provenance["viewport_can_trigger_analysis"] is False
    assert provenance["runtime_synthesizes_future_nodes"] is False
    assert provenance["runtime_mutates_harmonic_identity"] is False
    assert provenance["runtime_mutates_source_raw_prz"] is False
    assert provenance["runtime_owns_lifecycle"] is False
    assert provenance["authoritative_evidence"] is False
    assert provenance["writes_m4_evidence"] is False
    assert calls["instrument_ids"] == ["SSE.1", "SZSE.2"]
    assert calls["kwargs"]["expected_trade_date"] == "2026-09-22"


def test_runtime_degraded_cycle_requires_retry_when_any_instrument_failed(tmp_path) -> None:
    def snapshot_builder(service, instrument_ids, **kwargs):
        return _queue(failed=1)

    payload = execute_harmonic_analysis_cycle(
        object(),
        ["SSE.1", "SZSE.2"],
        cache_root=tmp_path,
        expected_trade_date="2026-09-22",
        input_identity=_identity(),
        snapshot_builder=snapshot_builder,
    )

    assert payload["healthy"] is False
    assert payload["overall_status"] == "degraded"
    assert payload["retry_required"] is True
    assert payload["failed_instrument_count"] == 1
    assert "不会推进成功水位" in payload["diagnostics_zh"][0]


def test_runtime_fails_closed_when_input_identity_changes_during_build(tmp_path) -> None:
    def snapshot_builder(service, instrument_ids, **kwargs):
        return _queue(stable=False)

    try:
        execute_harmonic_analysis_cycle(
            object(),
            ["SSE.1", "SZSE.2"],
            cache_root=tmp_path,
            expected_trade_date="2026-09-22",
            input_identity=_identity(),
            snapshot_builder=snapshot_builder,
        )
    except ValueError as exc:
        assert "changed during build" in str(exc)
    else:
        raise AssertionError("unstable input identity must fail closed")


def test_runtime_rejects_queue_that_claims_to_mutate_harmonic_identity(tmp_path) -> None:
    def snapshot_builder(service, instrument_ids, **kwargs):
        payload = _queue()
        payload["contract"]["mutates_harmonic_identity"] = True
        return payload

    try:
        execute_harmonic_analysis_cycle(
            object(),
            ["SSE.1", "SZSE.2"],
            cache_root=tmp_path,
            expected_trade_date="2026-09-22",
            input_identity=_identity(),
            snapshot_builder=snapshot_builder,
        )
    except ValueError as exc:
        assert "mutates_harmonic_identity" in str(exc)
    else:
        raise AssertionError("harmonic identity mutation claim must fail closed")


def test_provenance_is_viewport_independent_and_universe_bound() -> None:
    payload = build_analysis_runtime_provenance(
        expected_trade_date="2026-09-22",
        input_identity=_identity(),
        instrument_ids=["SZSE.2", "SSE.1"],
        bars=420,
        scales=(3, 5, 8, 13),
    )
    assert payload["expected_trade_date"] == "2026-09-22"
    assert payload["viewport_inputs_used"] is False
    assert payload["viewport_can_trigger_analysis"] is False
    assert payload["instrument_count"] == 2
    assert isinstance(payload["universe_hash"], str)
    assert len(payload["universe_hash"]) == 64


def test_status_file_round_trip_preserves_chinese_diagnostics(tmp_path) -> None:
    path = tmp_path / "runtime" / "harmonic.json"
    payload = empty_harmonic_analysis_runtime_status()
    payload["status"] = "healthy"
    payload["diagnostics_zh"] = ["自动谐波分析运行时正常。"]

    write_harmonic_analysis_runtime_status(path, payload)
    restored = read_harmonic_analysis_runtime_status(path)

    assert restored["status"] == "healthy"
    assert restored["diagnostics_zh"] == ["自动谐波分析运行时正常。"]
    assert not path.with_suffix(".json.tmp").exists()


def test_missing_status_is_explicit_not_started(tmp_path) -> None:
    payload = read_harmonic_analysis_runtime_status(tmp_path / "missing.json")
    assert payload["status"] == "not_started"
    assert payload["healthy"] is False
    assert "尚未产生运行状态" in payload["diagnostics_zh"][0]
