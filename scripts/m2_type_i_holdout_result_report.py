from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "research" / "m2-type-i-holdout-prereg-v1.json"
AUTHORIZATION = ROOT / "research" / "m2-type-i-holdout-open-v1.json"
RESULT = ROOT / "research" / "m2-type-i-holdout-result-v1.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    prereg = json.loads(PREREG.read_text(encoding="utf-8"))
    authorization = json.loads(AUTHORIZATION.read_text(encoding="utf-8"))
    result = json.loads(RESULT.read_text(encoding="utf-8"))

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    prereg_id = str(prereg.get("preregistration_id"))
    evaluation = authorization.get("evaluation") or {}
    primary = result.get("primary_contrast") or {}
    prereg_primary = prereg.get("primary_contrast") or {}
    prereg_exposure = (prereg_primary.get("exposure") or {}).get("name")
    prereg_comparator = (prereg_primary.get("comparator") or {}).get("name")
    multiplicity = result.get("multiplicity") or {}

    require(authorization.get("authorized") is False, "authorization must be closed")
    require(
        authorization.get("one_time_holdout_open") is False,
        "one_time_holdout_open must be false after the one-time evaluation",
    )
    require(authorization.get("evaluated_once") is True, "evaluated_once must be true")
    require(
        authorization.get("preregistration_id") == prereg_id,
        "authorization/preregistration id mismatch",
    )
    require(
        result.get("preregistration_id") == prereg_id,
        "result/preregistration id mismatch",
    )
    require(
        result.get("status") == "type_i_holdout_evaluated_once",
        "frozen result status is not the one-time evaluation status",
    )
    require(result.get("holdout_opened") is True, "frozen result must record the historical opening")
    require(result.get("holdout_consumed") is True, "frozen result must mark the Holdout consumed")
    require(
        evaluation.get("frozen_result_path") == str(RESULT.relative_to(ROOT)),
        "authorization points to the wrong frozen result path",
    )
    require(
        evaluation.get("frozen_result_sha256") == _sha256(RESULT),
        "frozen result SHA256 does not match authorization",
    )
    require(
        primary.get("exposure_name") == prereg_exposure,
        "frozen exposure group differs from preregistration",
    )
    require(
        primary.get("comparator_name") == prereg_comparator,
        "frozen comparator group differs from preregistration",
    )
    require(
        primary.get("result") in {"confirmed", "not_confirmed", "inconclusive"},
        "frozen primary result has an unsupported state",
    )
    require(
        primary.get("result") == evaluation.get("primary_result"),
        "authorization/result primary outcome mismatch",
    )
    require(multiplicity.get("primary_tests_run") == 1, "exactly one primary test must be recorded")
    require(
        multiplicity.get("alternate_thresholds_searched") is False,
        "alternate thresholds must remain unsearched",
    )
    require(
        multiplicity.get("alternate_endpoints_searched") is False,
        "alternate endpoints must remain unsearched",
    )

    if failures:
        for failure in failures:
            print(f"[HT-CN M2 HOLDOUT FROZEN] FAIL: {failure}")
        return 2

    exposure = primary.get("exposure") or {}
    comparator = primary.get("comparator") or {}
    interval = primary.get("newcombe_95_ci") or {}
    print(
        "[HT-CN M2 HOLDOUT FROZEN] "
        f"status=verified_closed, prereg={prereg_id}, result={primary.get('result')}"
    )
    print(
        "[HT-CN M2 HOLDOUT FROZEN] primary "
        f"{primary.get('exposure_name')}: n={exposure.get('records')}, hits={exposure.get('endpoint_hits')}, "
        f"rate={exposure.get('endpoint_rate')}; {primary.get('comparator_name')}: "
        f"n={comparator.get('records')}, hits={comparator.get('endpoint_hits')}, "
        f"rate={comparator.get('endpoint_rate')}"
    )
    print(
        "[HT-CN M2 HOLDOUT FROZEN] effect="
        f"{primary.get('absolute_rate_difference')}, CI95=[{interval.get('lower')}, {interval.get('upper')}]"
    )
    print("[HT-CN M2 HOLDOUT FROZEN] HOLDOUT CONSUMED/CLOSED; no recomputation performed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
