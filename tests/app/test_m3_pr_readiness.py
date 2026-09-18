from scripts.m3_pr_readiness import evaluate, render_markdown


HEAD = "abc123"


def _workbench(status="pass"):
    return {
        "code_head": HEAD,
        "worktree_clean": True,
        "dirty_paths": [],
        "status": status,
        "gates": {
            "python": {"status": "pass"},
            "web_build": {"status": "pass"},
            "real_m1_metadata": {"status": "pass"},
            "real_m1_product_contract": {"status": "pass"},
            "local_services": {"status": "pass"},
            "playwright": {"status": "pass"},
        },
    }


def _metadata():
    return {
        "code_head": HEAD,
        "worktree_clean": True,
        "dirty_paths": [],
        "status": "pass",
        "event_feed_status": "event_partial",
        "samples": [
            {"instrument_id": "SSE.600000", "board_expected": "MAIN", "metadata_loaded": True, "parquet_loaded": True, "logical_last_trade_date": "2026-09-17"},
            {"instrument_id": "SSE.688001", "board_expected": "STAR", "metadata_loaded": True, "parquet_loaded": True, "logical_last_trade_date": "2026-09-17"},
            {"instrument_id": "SZSE.300001", "board_expected": "CHINEXT", "metadata_loaded": True, "parquet_loaded": True, "logical_last_trade_date": "2026-09-17"},
        ],
    }


def _product(patterns=2):
    return {
        "code_head": HEAD,
        "worktree_clean": True,
        "dirty_paths": [],
        "status": "pass",
        "total_issues": 0,
        "successful_analyses": 3,
        "total_patterns": patterns,
        "samples": [
            {"instrument_id": "SSE.688001", "analysis_status": "success", "last_trade_date": "2026-09-17"},
        ],
    }


def _context(overall="all_steps_completed"):
    return {
        "code_head": HEAD,
        "worktree_clean": True,
        "dirty_paths": [],
        "overall": overall,
        "expected_trade_date": "2026-09-17",
        "target_trade_date": "2026-09-17",
        "local_trade_calendar_latest": "2026-09-17",
        "logical_market_latest": "2026-09-17",
        "market_dataset_coverage": {
            "initialized_dataset_count": 3,
            "current_dataset_count": 3,
            "stale_dataset_count": 0,
            "ahead_dataset_count": 0,
        },
        "layers": {
            "market_data_freshness": {"state": "current"},
            "execution_event": {
                "state": "partial_positive_evidence",
                "coverage_scope": "positive_evidence_only",
            },
            "market": {"state": "current"},
            "industry": {"state": "current"},
            "concept": {"state": "current"},
        },
    }


def test_ready_with_known_event_warning() -> None:
    result = evaluate(
        current_head=HEAD,
        workbench=_workbench(),
        metadata=_metadata(),
        product=_product(),
        context=_context(),
    )
    assert result["pr_ready"] is True
    assert result["status"] == "ready_with_warnings"
    assert result["blocker_count"] == 0
    assert result["warning_count"] >= 1


def test_stale_report_is_hard_blocker() -> None:
    workbench = _workbench()
    workbench["code_head"] = "old"
    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=_metadata(),
        product=_product(),
        context=_context(),
    )
    assert result["pr_ready"] is False
    assert any(item["code"] == "workbench_report_stale" for item in result["blockers"])


def test_context_structural_failure_blocks_ready() -> None:
    context = _context("partial_failure")
    context["layers"]["industry"] = {"state": "failed"}
    result = evaluate(
        current_head=HEAD,
        workbench=_workbench(),
        metadata=_metadata(),
        product=_product(),
        context=context,
    )
    assert result["pr_ready"] is False
    assert any(item["code"] == "context_industry_failed" for item in result["blockers"])


def test_no_real_pattern_is_warning_not_false_contract_failure() -> None:
    result = evaluate(
        current_head=HEAD,
        workbench=_workbench(),
        metadata=_metadata(),
        product=_product(patterns=0),
        context=_context(),
    )
    assert result["pr_ready"] is True
    assert any(item["code"] == "real_m1_no_pattern_observed" for item in result["warnings"])


def test_human_readable_report_exposes_ready_and_findings() -> None:
    result = evaluate(
        current_head=HEAD,
        workbench=_workbench(),
        metadata=_metadata(),
        product=_product(),
        context=_context(),
    )
    rendered = render_markdown(result)
    assert "READY（有已知警告）" in rendered
    assert "硬阻断" in rendered
    assert "警告" in rendered
    assert "Daily event" in rendered


def test_external_context_unavailable_is_warning_not_blocker() -> None:
    workbench = _workbench()
    metadata = _metadata()
    product = _product()
    context = _context("degraded")
    context["layers"]["market"] = {"state": "partial"}
    context["layers"]["industry"] = {"state": "external_unavailable"}
    context["layers"]["concept"] = {"state": "external_unavailable"}

    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )

    assert result["pr_ready"] is True
    warning_codes = {item["code"] for item in result["warnings"]}
    assert "context_sync_degraded" in warning_codes
    assert "context_industry_external_unavailable" in warning_codes
    assert "context_concept_external_unavailable" in warning_codes


def test_local_context_failure_remains_hard_blocker() -> None:
    workbench = _workbench()
    metadata = _metadata()
    product = _product()
    context = _context("partial_failure")
    context["layers"]["industry"] = {"state": "failed"}

    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )

    assert result["pr_ready"] is False
    blocker_codes = {item["code"] for item in result["blockers"]}
    assert "context_sync_partial_failure" in blocker_codes
    assert "context_industry_failed" in blocker_codes
