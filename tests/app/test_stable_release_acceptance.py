from pathlib import Path

from htcn.app.stable_release_acceptance import evaluate_stable_release_acceptance

ROOT = Path(__file__).resolve().parents[2]


def _release_report() -> dict[str, object]:
    return {
        "status": "built",
        "release_head": "1" * 40,
        "release_version": "0.1.0",
        "package_sha256": "2" * 64,
        "private_market_data_included": False,
        "mutable_data_included": False,
        "verification": {"verified": True},
        "packaged_runtime_validation": {
            "status": "success",
            "checks": {
                "m4_methodology": {"exit_code": 0},
                "m4_outcome_engine": {"exit_code": 0},
                "product_preflight": {"exit_code": 0},
            },
        },
    }


def test_m9_6_stable_release_contract_accepts_activated_candidate() -> None:
    payload = evaluate_stable_release_acceptance(ROOT, release_report=_release_report())
    assert payload["accepted"] is True
    assert payload["statistical_claims_unlocked_by_this_acceptance"] is False
    assert payload["user_computer_required"] is False
    assert payload["is_trade_instruction"] is False


def test_m9_6_stable_release_rejects_unverified_package() -> None:
    report = _release_report()
    report["verification"] = {"verified": False}
    payload = evaluate_stable_release_acceptance(ROOT, release_report=report)
    assert payload["accepted"] is False
    checks = {row["name"]: row for row in payload["checks"]}
    assert checks["verified_release_package"]["passed"] is False
