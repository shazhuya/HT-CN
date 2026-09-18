from scripts.m3_pr_readiness import evaluate


HEAD = "abc123"


def _workbench(status="pass"):
    return {
        "code_head": HEAD,
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
        "status": "pass",
        "event_feed_status": "event_partial",
        "samples": [
            {"board_expected": "MAIN", "metadata_loaded": True, "parquet_loaded": True},
            {"board_expected": "STAR", "metadata_loaded": True, "parquet_loaded": True},
            {"board_expected": "CHINEXT", "metadata_loaded": True, "parquet_loaded": True},
        ],
    }


def _product(patterns=2):
    return {
        "code_head": HEAD,
        "status": "pass",
        "total_issues": 0,
        "successful_analyses": 3,
        "total_patterns": patterns,
    }


def _context(overall="all_steps_completed"):
    return {
        "code_head": HEAD,
        "overall": overall,
        "layers": {
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
