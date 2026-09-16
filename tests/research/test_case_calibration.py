from htcn.research.case_calibration import (
    build_completed_case_record,
    canonical_case_key,
    dedupe_case_records,
)


def _base_pattern(*, schema: str = "XABCD", scale: int = 5, t1=4, t2=9) -> dict:
    labels = {
        "XABCD": ("X", "A", "B", "C", "D"),
        "ABCD": ("A", "B", "C", "D"),
        "0XABC": ("0", "X", "A", "B", "C"),
        "FIVE_ZERO": ("X", "A", "B", "C", "D"),
    }[schema]
    prices = {
        "XABCD": (100.0, 120.0, 108.0, 116.0, 104.0),
        "ABCD": (120.0, 100.0, 112.0, 92.0),
        "0XABC": (100.0, 120.0, 110.0, 130.0, 102.0),
        "FIVE_ZERO": (100.0, 120.0, 96.0, 135.0, 115.5),
    }[schema]
    points = [
        {"label": label, "index": 10 + index * 5, "price": price, "trade_date": f"2026-01-{index + 1:02d}"}
        for index, (label, price) in enumerate(zip(labels, prices))
    ]
    pattern = {
        "pattern_id": "shark" if schema == "0XABC" else ("five_zero" if schema == "FIVE_ZERO" else "bat"),
        "schema": schema,
        "direction": "bullish",
        "state": "completed",
        "scale": scale,
        "geometry_score": 88.0,
        "is_primary_identity": True,
        "points": points,
        "metrics": {},
        "checks": [],
        "pivot_support": [
            {"label": point["label"], "support_count": 2, "scales": [3, 5]}
            for point in points
        ],
        "prz": {
            "price_low": 100.0,
            "price_high": 102.0,
            "width": 2.0,
            "components": [],
        },
    }
    if schema == "0XABC":
        pattern["reaction_targets"] = {
            "bars_to_50": t1,
            "bars_to_618": t2,
            "bars_to_reciprocal_abcd": 7,
        }
    else:
        pattern["reaction_audit"] = {
            "bars_to_382": t1,
            "bars_to_618": t2,
            "type_ii_evidence_state": "price_and_rsi_confirmed",
        }
    return pattern


def test_standard_completed_case_keeps_identity_and_outcome_separate() -> None:
    record = build_completed_case_record(
        _base_pattern(),
        instrument_id="SSE.688256",
        price_mode="qfq",
        bars_returned=80,
        observation_horizon=20,
    )

    assert record["identity"]["identity_valid"] is True
    assert record["outcome"]["outcome_class"] == "t2_within_horizon"
    assert record["outcome"]["family"] == "type_i_382_618"
    assert record["audit_policy"]["outcome_changes_identity"] is False
    assert record["quality"]["reference_span_name"] == "XA"


def test_shark_uses_its_own_50_618_reaction_family() -> None:
    record = build_completed_case_record(
        _base_pattern(schema="0XABC", t1=3, t2=12),
        instrument_id="SZSE.300001",
        price_mode="qfq",
        bars_returned=80,
        observation_horizon=10,
    )

    assert record["outcome"]["family"] == "shark_reaction_50_618"
    assert record["outcome"]["t1_name"] == "50%"
    assert record["outcome"]["t2_name"] == "61.8%"
    assert record["outcome"]["outcome_class"] == "t1_only_within_horizon"
    assert record["quality"]["reference_span_name"] == "0B"


def test_maturity_prevents_recent_case_from_being_called_negative() -> None:
    pattern = _base_pattern(t1=None, t2=None)
    record = build_completed_case_record(
        pattern,
        instrument_id="SSE.600000",
        price_mode="qfq",
        bars_returned=pattern["points"][-1]["index"] + 6,
        observation_horizon=20,
    )

    assert record["outcome"]["available_future_bars"] == 5
    assert record["outcome"]["outcome_class"] == "immature"


def test_five_zero_normalizes_prz_to_bc_span() -> None:
    record = build_completed_case_record(
        _base_pattern(schema="FIVE_ZERO"),
        instrument_id="SSE.600519",
        price_mode="qfq",
        bars_returned=90,
    )
    assert record["quality"]["reference_span_name"] == "BC"
    assert record["quality"]["reference_span"] == 39.0


def test_dedupe_never_uses_outcome_to_choose_cross_scale_representative() -> None:
    weak_geometry = build_completed_case_record(
        _base_pattern(scale=3, t1=1, t2=2),
        instrument_id="SSE.688256",
        price_mode="qfq",
        bars_returned=80,
    )
    stronger_pattern = _base_pattern(scale=13, t1=None, t2=None)
    stronger_pattern["geometry_score"] = 95.0
    stronger_pattern["pivot_support"] = [
        {"label": point["label"], "support_count": 3, "scales": [3, 5, 13]}
        for point in stronger_pattern["points"]
    ]
    strong_geometry = build_completed_case_record(
        stronger_pattern,
        instrument_id="SSE.688256",
        price_mode="qfq",
        bars_returned=80,
    )

    deduped = dedupe_case_records([weak_geometry, strong_geometry])
    assert len(deduped) == 1
    assert deduped[0]["identity"]["scale"] == 13
    assert deduped[0]["observed_scales"] == [3, 13]
    assert canonical_case_key(weak_geometry) == canonical_case_key(strong_geometry)
