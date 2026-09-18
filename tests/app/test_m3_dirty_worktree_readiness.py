from scripts.m3_pr_readiness import evaluate


def test_dirty_evidence_report_is_hard_blocker() -> None:
    head = "abc"
    base = {
        "code_head": head,
        "worktree_clean": True,
    }
    workbench = {
        **base,
        "status": "pass",
        "gates": {
            "python":{"status":"pass"},
            "web_build":{"status":"pass"},
            "real_m1_metadata":{"status":"pass"},
            "real_m1_product_contract":{"status":"pass"},
            "local_services":{"status":"pass"},
            "playwright":{"status":"pass"},
        },
    }
    metadata = {
        **base,
        "status":"pass",
        "event_feed_status":"event_complete",
        "samples":[
            {"instrument_id":"A","board_expected":"MAIN","metadata_loaded":True,"parquet_loaded":True,"logical_last_trade_date":"2026-09-17"},
            {"instrument_id":"B","board_expected":"STAR","metadata_loaded":True,"parquet_loaded":True,"logical_last_trade_date":"2026-09-17"},
            {"instrument_id":"C","board_expected":"CHINEXT","metadata_loaded":True,"parquet_loaded":True,"logical_last_trade_date":"2026-09-17"},
        ],
    }
    product = {
        **base,
        "status":"pass",
        "total_issues":0,
        "successful_analyses":1,
        "total_patterns":1,
        "samples":[{"instrument_id":"B","analysis_status":"success","last_trade_date":"2026-09-17"}],
    }
    context = {
        **base,
        "overall":"all_steps_completed",
        "expected_trade_date":"2026-09-17",
        "target_trade_date":"2026-09-17",
        "local_trade_calendar_latest":"2026-09-17",
        "logical_market_latest":"2026-09-17",
        "market_dataset_coverage":{
            "initialized_dataset_count":3,
            "current_dataset_count":3,
            "stale_dataset_count":0,
            "ahead_dataset_count":0,
        },
        "layers":{
            "market_data_freshness":{"state":"current"},
            "execution_event":{"state":"partial_positive_evidence"},
            "market":{"state":"current"},
            "industry":{"state":"current"},
            "concept":{"state":"current"},
        },
    }

    product["worktree_clean"] = False
    product["dirty_paths"] = ["src/x.py"]
    result = evaluate(
        current_head=head,
        workbench=workbench,
        metadata=metadata,
        product=product,
        context=context,
    )
    assert result["pr_ready"] is False
    assert any(item["code"] == "product_evidence_dirty_worktree" for item in result["blockers"])
