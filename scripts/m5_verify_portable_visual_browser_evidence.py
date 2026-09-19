from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = (
    ROOT
    / "artifacts"
    / "reports"
    / "playwright"
    / "phase18-portable-visual-browser-evidence.json"
)

REQUIRED_CHECKS = {
    "completed_xabcd_nodes_and_legs",
    "layer_toggle_source_ideal_envelope",
    "source_clock_events",
    "non_geometry_price_guides",
    "identity_conflict_disclosure",
    "forming_xabcd_missing_d_not_rendered",
    "standalone_abcd_topology_and_ratios",
    "shark_0xabc_without_d",
    "forming_shark_missing_c_not_rendered",
    "five_zero_618_refinement_not_raw_prz",
    "component_layer_toggle",
}

REQUIRED_SCREENSHOT_BASENAMES = {
    "m5-phase18-xabcd-complete.png",
    "m5-phase18-xabcd-forming.png",
    "m5-phase18-abcd-complete.png",
    "m5-phase18-shark.png",
    "m5-phase18-shark-forming.png",
    "m5-phase18-five-zero.png",
}


def _sha256_path(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    if not EVIDENCE.is_file():
        raise SystemExit("phase18_evidence_missing")

    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("phase18_evidence_not_object")

    if int(payload.get("schema_version") or 0) != 1:
        raise SystemExit("phase18_evidence_schema_invalid")
    if payload.get("phase") != "M5 Phase 18":
        raise SystemExit("phase18_evidence_phase_invalid")
    if int(payload.get("visual_semantics_version") or 0) != 2:
        raise SystemExit("phase18_visual_semantics_version_invalid")
    if int(payload.get("transport_schema_version") or 0) != 4:
        raise SystemExit("phase18_transport_schema_version_invalid")
    if payload.get("browser") != "chromium":
        raise SystemExit("phase18_browser_invalid")

    for field in (
        "no_market_database_required",
    ):
        if payload.get(field) is not True:
            raise SystemExit(f"phase18_boundary_invalid:{field}")

    for field in (
        "writes_m4_evidence",
        "mutates_harmonic_identity",
        "mutates_source_raw_prz",
        "mutates_source_lifecycle",
        "future_pattern_points_rendered",
        "is_trade_instruction",
    ):
        if payload.get(field) is not False:
            raise SystemExit(f"phase18_boundary_invalid:{field}")

    checks = {
        str(value)
        for value in (payload.get("checks") or [])
        if value
    }
    missing_checks = REQUIRED_CHECKS.difference(checks)
    if missing_checks:
        raise SystemExit(
            "phase18_required_checks_missing:"
            + ",".join(sorted(missing_checks))
        )

    screenshots = payload.get("screenshots")
    if not isinstance(screenshots, list):
        raise SystemExit("phase18_screenshots_invalid")
    if int(payload.get("screenshot_count") or -1) != len(screenshots):
        raise SystemExit("phase18_screenshot_count_mismatch")

    actual_basenames: set[str] = set()
    for record in screenshots:
        if not isinstance(record, dict):
            raise SystemExit("phase18_screenshot_record_invalid")
        raw_file = str(record.get("file") or "")
        path = (ROOT / "apps" / "web" / raw_file).resolve()
        if not path.is_file():
            # Playwright records ../../artifacts/... relative to apps/web.
            path = (ROOT / raw_file).resolve()
        if not path.is_file():
            raise SystemExit(f"phase18_screenshot_missing:{raw_file}")

        basename = path.name
        actual_basenames.add(basename)
        size = path.stat().st_size
        if size <= 10_000:
            raise SystemExit(f"phase18_screenshot_too_small:{basename}")
        if int(record.get("size_bytes") or -1) != size:
            raise SystemExit(f"phase18_screenshot_size_mismatch:{basename}")
        if str(record.get("sha256") or "") != _sha256_path(path):
            raise SystemExit(f"phase18_screenshot_hash_mismatch:{basename}")

    if actual_basenames != REQUIRED_SCREENSHOT_BASENAMES:
        raise SystemExit(
            "phase18_screenshot_set_mismatch:"
            + ",".join(sorted(actual_basenames))
        )

    print(
        json.dumps(
            {
                "status": "valid",
                "required_check_count": len(REQUIRED_CHECKS),
                "screenshot_count": len(screenshots),
                "visual_semantics_version": 2,
                "transport_schema_version": 4,
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
