from __future__ import annotations

from collections import Counter

from scripts.m4_capture_lifecycle_snapshot import (
    _confirmed_full_day_suspensions,
    _summary_counter,
    _validate_capture_trade_date,
)


def test_snapshot_summary_is_transparent_raw_count_not_score() -> None:
    assert _summary_counter(["waiting", "waiting", "execution_evaluation"]) == {
        "execution_evaluation": 1,
        "waiting": 2,
    }


def test_counter_has_no_weighting_or_rank_semantics() -> None:
    values = ["type_i_confirmed", "waiting_terminal", "waiting_terminal"]
    summary = _summary_counter(values)
    assert summary == dict(sorted(Counter(values).items()))
    assert "score" not in summary


def test_partial_universe_is_diagnostic_only() -> None:
    # The authoritative capture contract must never treat max_symbols as full coverage.
    # This test intentionally checks the source-level contract without requiring M1.
    import inspect
    from scripts import m4_capture_lifecycle_snapshot as capture

    source = inspect.getsource(capture.run)
    assert 'diagnostic_partial_universe_no_commit' in source
    assert 'authoritative transaction/journal/manifest writes are disabled' in source


def test_capture_trade_date_requires_provider_local_alignment() -> None:
    assert _validate_capture_trade_date(
        local_trade_date="2026-09-18",
        provider_trade_date="2026-09-18",
    ) == "2026-09-18"

    try:
        _validate_capture_trade_date(
            local_trade_date="2026-09-17",
            provider_trade_date="2026-09-18",
        )
    except RuntimeError as exc:
        assert "does not match provider-confirmed" in str(exc)
    else:
        raise AssertionError("stale local trade date must fail closed")


def test_confirmed_full_day_suspension_query_excludes_intraday(tmp_path) -> None:
    import duckdb

    catalog = tmp_path / "catalog.duckdb"
    with duckdb.connect(str(catalog)) as con:
        con.execute(
            """
            CREATE TABLE security_daily_event (
                instrument_id VARCHAR,
                trade_date DATE,
                trading_status VARCHAR,
                no_price_limit BOOLEAN,
                price_limit_pct_override DOUBLE,
                resolution_complete BOOLEAN,
                source VARCHAR,
                reason VARCHAR,
                updated_at TIMESTAMP
            )
            """
        )
        con.execute(
            """
            INSERT INTO security_daily_event VALUES
            ('SSE.600000', '2026-09-18', 'suspended', NULL, NULL, FALSE, 'feed', 'full', CURRENT_TIMESTAMP),
            ('SSE.600001', '2026-09-18', 'intraday_suspended', NULL, NULL, FALSE, 'feed', 'intra', CURRENT_TIMESTAMP),
            ('SSE.600002', '2026-09-17', 'suspended', NULL, NULL, FALSE, 'feed', 'old', CURRENT_TIMESTAMP)
            """
        )

    events = _confirmed_full_day_suspensions(catalog, "2026-09-18")
    assert set(events) == {"SSE.600000"}
    assert events["SSE.600000"]["reason"] == "full"


def test_confirmed_full_day_suspension_query_allows_optional_missing_table(tmp_path) -> None:
    import duckdb

    catalog = tmp_path / "catalog.duckdb"
    with duckdb.connect(str(catalog)):
        pass
    assert _confirmed_full_day_suspensions(catalog, "2026-09-18") == {}
