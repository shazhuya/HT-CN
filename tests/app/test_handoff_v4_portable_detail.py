from __future__ import annotations

import json
import zipfile
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from htcn.app import handoff_v4_inspector as inspector
from htcn.app import handoff_v4_portable_detail as detail

FP = "a" * 64


def _valid_v3(path: Path) -> SimpleNamespace:
    return SimpleNamespace(
        status="valid",
        schema_version=3,
        file_count=1,
        errors=(),
        warnings=(),
        manifest={},
    )


def _pattern() -> dict:
    return {
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "state": "completed",
        "is_primary_identity": True,
        "points": [
            {"label": "X", "index": 4, "price": 100.0, "trade_date": "2026-08-20"},
            {"label": "A", "index": 8, "price": 120.0, "trade_date": "2026-08-26"},
            {"label": "B", "index": 12, "price": 110.0, "trade_date": "2026-09-01"},
            {"label": "C", "index": 17, "price": 116.0, "trade_date": "2026-09-08"},
            {"label": "D", "index": 23, "price": 102.0, "trade_date": "2026-09-16"},
        ],
        "prz": {
            "source_prz": {
                "available": True,
                "price_low": 101.5,
                "price_high": 103.0,
            },
            "components": [],
        },
        "source_lifecycle": {
            "state": "t_plus_1",
            "source_prz_low": 101.5,
            "source_prz_high": 103.0,
            "source_terminal_bar": 23,
            "execution_start_bar": 24,
            "type_i_t1_bar": None,
            "type_i_t2_bar": None,
            "type_ii_terminal_bar": None,
            "reversal_exit_after_type_ii_bar": None,
        },
        "decision_narrative": {
            "action_state": "reaction_observation",
        },
    }


def _bars() -> list[dict]:
    rows = []
    for index in range(30):
        close = 105.0 + (index % 5)
        rows.append(
            {
                "index": index,
                "trade_date": f"2026-09-{index + 1:02d}",
                "open": close - 0.5,
                "high": close + 1.0,
                "low": close - 1.0,
                "close": close,
                "volume": 1000 + index,
            }
        )
    rows[-1]["trade_date"] = "2026-09-19"
    return rows


def _inspection() -> dict:
    pattern = _pattern()
    key = detail._display_key("SSE.688256", pattern)
    queue_item = {
        "display_key": key,
        "instrument_id": "SSE.688256",
        "pattern_id": "bat",
        "schema": "XABCD",
        "direction": "bullish",
        "scale": 5,
        "pattern_state": "completed",
        "action_state": "reaction_observation",
        "lifecycle_state": "t_plus_1",
        "current_position": "T-Bar 后观察期",
        "first_watch": "先看 Type-I 38.2%",
        "next_watch": "再看 61.8%",
        "upgrade_blocker": "尚未到达 T1",
        "next_key_price": 108.5,
        "next_key_price_role": "type_i_38_2_target",
        "context_cautions": [],
    }
    return {
        "summary": {"trade_date": "2026-09-19"},
        "current_product_snapshot": {
            "input_identity": {"fingerprint": FP},
        },
        "indexes": {"current_queue_items": [queue_item]},
    }


class Provider:
    def __init__(self, *, include_pattern: bool = True) -> None:
        self.include_pattern = include_pattern

    def analyze(
        self,
        instrument_id: str,
        *,
        bars: int,
        scales: tuple[int, ...],
    ) -> dict:
        return {
            "instrument_id": instrument_id,
            "last_trade_date": "2026-09-19",
            "price_mode": "qfq",
            "warning": None,
            "bars": _bars(),
            "completed": [_pattern()] if self.include_pattern else [],
            "forming": [],
        }


def _patch_v3(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        detail,
        "verify_daily_handoff_bundle_v3",
        lambda path: _valid_v3(Path(path)),
    )
    monkeypatch.setattr(
        detail,
        "build_handoff_v3_inspection",
        lambda path: _inspection(),
    )
    monkeypatch.setattr(
        inspector,
        "build_handoff_v3_inspection",
        lambda path: _inspection(),
    )


def test_v4_builds_complete_exact_detail_transport(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v3(monkeypatch)
    v3 = tmp_path / "v3.zip"
    v3.write_bytes(b"verified-v3-placeholder")
    output = tmp_path / "v4.zip"

    payload = detail.build_daily_handoff_bundle_v4(
        v3_bundle=v3,
        analysis_provider=Provider(),
        current_input_identity_fingerprint=FP,
        output=output,
    )

    assert payload["status"] == "complete_detail_transport"
    assert payload["queue_display_key_count"] == 1
    assert payload["detail_display_key_count"] == 1
    assert payload["error_display_key_count"] == 0
    checked = detail.verify_daily_handoff_bundle_v4(output)
    assert checked.status == "valid"
    assert checked.detail_display_key_count == 1


def test_v4_rejects_input_identity_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v3(monkeypatch)
    v3 = tmp_path / "v3.zip"
    v3.write_bytes(b"verified-v3-placeholder")

    with pytest.raises(
        RuntimeError,
        match="portable_detail_input_identity_mismatch",
    ):
        detail.build_daily_handoff_bundle_v4(
            v3_bundle=v3,
            analysis_provider=Provider(),
            current_input_identity_fingerprint="b" * 64,
            output=tmp_path / "v4.zip",
        )


def test_v4_missing_exact_pattern_is_explicit_degraded_not_silent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v3(monkeypatch)
    v3 = tmp_path / "v3.zip"
    v3.write_bytes(b"verified-v3-placeholder")
    output = tmp_path / "v4.zip"

    payload = detail.build_daily_handoff_bundle_v4(
        v3_bundle=v3,
        analysis_provider=Provider(include_pattern=False),
        current_input_identity_fingerprint=FP,
        output=output,
    )

    assert payload["status"] == "detail_transport_degraded"
    assert payload["detail_display_key_count"] == 0
    assert payload["error_display_key_count"] == 1
    checked = detail.verify_daily_handoff_bundle_v4(output)
    assert checked.status == "valid"
    assert checked.queue_display_key_count == (
        checked.detail_display_key_count + checked.error_display_key_count
    )


def test_v4_verifier_detects_semantic_pattern_tamper_with_updated_member_hash(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v3(monkeypatch)
    v3 = tmp_path / "v3.zip"
    v3.write_bytes(b"verified-v3-placeholder")
    original = tmp_path / "v4.zip"
    detail.build_daily_handoff_bundle_v4(
        v3_bundle=v3,
        analysis_provider=Provider(),
        current_input_identity_fingerprint=FP,
        output=original,
    )

    with zipfile.ZipFile(original, "r") as source:
        blobs = {
            info.filename: source.read(info.filename)
            for info in source.infolist()
        }
    detail_name = next(
        name
        for name in blobs
        if name.startswith("detail/instruments/")
    )
    payload = json.loads(blobs[detail_name].decode("utf-8"))
    payload["patterns"][0]["pattern"]["points"][0]["trade_date"] = "2026-08-21"
    blobs[detail_name] = (
        json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    manifest = json.loads(
        blobs["daily-handoff-v4-manifest.json"].decode("utf-8")
    )
    for record in manifest["files"]:
        if record["arcname"] == detail_name:
            record["size_bytes"] = len(blobs[detail_name])
            record["sha256"] = sha256(blobs[detail_name]).hexdigest()
    blobs["daily-handoff-v4-manifest.json"] = (
        json.dumps(
            manifest,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    ).encode("utf-8")

    tampered = tmp_path / "tampered-v4.zip"
    with zipfile.ZipFile(
        tampered,
        "w",
        compression=zipfile.ZIP_DEFLATED,
    ) as target:
        for name, data in blobs.items():
            target.writestr(name, data)

    checked = detail.verify_daily_handoff_bundle_v4(tampered)
    assert checked.status == "invalid"
    assert "detail_display_key_derivation_mismatch" in checked.errors


def test_v4_visual_inspector_is_portable_and_does_not_fake_future_leg(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_v3(monkeypatch)
    v3 = tmp_path / "v3.zip"
    v3.write_bytes(b"verified-v3-placeholder")
    output = tmp_path / "v4.zip"
    detail.build_daily_handoff_bundle_v4(
        v3_bundle=v3,
        analysis_provider=Provider(),
        current_input_identity_fingerprint=FP,
        output=output,
    )

    payload = inspector.build_handoff_v4_inspection(output)
    html = inspector.build_portable_pattern_review_html(payload)

    assert payload["contract"]["requires_market_database"] is False
    assert payload["summary"]["detail_complete"] is True
    assert len(payload["details_by_display_key"]) == 1
    transported = next(iter(payload["details_by_display_key"].values()))
    assert transported["pattern"]["points"][0]["price"] == 100.0
    assert "不是预测腿" in html
    assert "Source PRZ" in html
    assert "fmt(q.price)" in html
    assert "fetch(" not in html
    assert "review-session/event" not in html
