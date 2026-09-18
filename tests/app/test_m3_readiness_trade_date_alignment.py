from scripts.m3_pr_readiness import evaluate


HEAD = "abc123"


def _reports(expected="2026-09-17"):
    workbench = {
        "code_head": HEAD,
        "status": "pass",
        "gates": {
            "python": {"status": "pass"},
            "web_build": {"status": "pass"},
            "real_m1_metadata": {"status": "pass"},
            "real_m1_product_contract": {"status": "pass"},
            "local_services": {"status": "pass"},
            "playwright": {"status": "pass"},
        },
    }
    metadata = {
        "code_head": HEAD,
        "status": "pass",
        "event_feed_status": "event_partial",
        "samples": [
            {
                "instrument_id": "SSE.600000",
                "board_expected": "MAIN",
                "metadata_loaded": True,
                "parquet_loaded": True,
                "logical_last_trade_date": expected,
            },
            {
                "instrument_id": "SSE.688001",
                "board_expected": "STAR",
                "metadata_loaded": True,
                "parquet_loaded": True,
                "logical_last_trade_date": expected,
            },
            {
                "instrument_id": "SZSE.300001",
                "board_expected": "CHINEXT",
                "metadata_loaded": True,
                "parquet_loaded": True,
                "logical_last_trade_date": expected,
            },
        ],
    }
    product = {
        "code_head": HEAD,
        "status": "pass",
        "total_issues": 0,
        "successful_analyses": 2,
        "total_patterns": 1,
        "samples": [
            {"instrument_id": "SSE.688001", "analysis_status": "success", "last_trade_date": expected},
            {"instrument_id": "SZSE.300001", "analysis_status": "success", "last_trade_date": expected},
        ],
    }
    context = {
        "code_head": HEAD,
        "overall": "all_steps_completed",
        "expected_trade_date": expected,
        "target_trade_date": expected,
        "local_trade_calendar_latest": expected,
        "logical_market_latest": expected,
        "market_dataset_coverage": {
            "initialized_dataset_count": 3,
            "current_dataset_count": 3,
            "stale_dataset_count": 0,
            "ahead_dataset_count": 0,
        },
        "layers": {
            "market_data_freshness": {"state": "current"},
            "execution_event": {"state": "partial_positive_evidence", "coverage_scope": "positive_evidence_only"},
            "market": {"state": "current"},
            "industry": {"state": "current"},
            "concept": {"state": "current"},
        },
    }
    return workbench, metadata, product, context


def test_current_trade_date_alignment_can_be_ready() -> None:
    workbench, metadata, product, context = _reports()
    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )
    assert result["pr_ready"] is True


def test_stale_metadata_sample_blocks_ready() -> None:
    workbench, metadata, product, context = _reports()
    metadata["samples"][0]["logical_last_trade_date"] = "2026-09-16"
    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )
    assert result["pr_ready"] is False
    assert any(item["code"] == "real_m1_metadata_trade_date_mismatch" for item in result["blockers"])


def test_stale_product_sample_blocks_ready() -> None:
    workbench, metadata, product, context = _reports()
    product["samples"][0]["last_trade_date"] = "2026-09-16"
    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )
    assert result["pr_ready"] is False
    assert any(item["code"] == "real_m1_product_trade_date_mismatch" for item in result["blockers"])


def test_stale_local_market_date_blocks_ready() -> None:
    workbench, metadata, product, context = _reports()
    context["logical_market_latest"] = "2026-09-16"
    result = evaluate(
        current_head=HEAD,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )
    assert result["pr_ready"] is False
    assert any(item["code"] == "logical_market_trade_date_mismatch" for item in result["blockers"])
