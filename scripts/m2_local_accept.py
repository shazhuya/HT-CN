from __future__ import annotations

import math
from pathlib import Path

from htcn.app.harmonic_service import DatasetNotFoundError, LocalHarmonicService

ROOT = Path(__file__).resolve().parents[1]
DATA_ROOT = ROOT / "data" / "market"
PILOT_PRIORITY = ("SSE.688256", "SZSE.300820", "SSE.600519")


def _factor_symbols() -> list[str]:
    root = DATA_ROOT / "adjustment" / "qfq"
    if not root.exists():
        return []
    symbols = sorted(path.stem for path in root.glob("*.parquet"))
    priority = [symbol for symbol in PILOT_PRIORITY if symbol in symbols]
    remainder = [symbol for symbol in symbols if symbol not in priority]
    return priority + remainder


def _assert_finite_pattern(pattern: dict) -> None:
    assert pattern["points"], "pattern has no points"
    indices = [int(point["index"]) for point in pattern["points"]]
    assert indices == sorted(indices), f"pattern indices are not increasing: {indices}"
    for point in pattern["points"]:
        assert math.isfinite(float(point["price"])) and float(point["price"]) > 0
    prz = pattern["prz"]
    assert 0 < float(prz["price_low"]) <= float(prz["price_high"])
    assert math.isfinite(float(pattern["geometry_score"]))
    assert 0 <= float(pattern["geometry_score"]) <= 100


def main() -> int:
    print("[HT-CN M2 LOCAL] Real local-data harmonic acceptance...")
    service = LocalHarmonicService(DATA_ROOT)
    symbols = _factor_symbols()
    if not symbols:
        print("[HT-CN M2 LOCAL] FAIL: no QFQ factor datasets. Run M1 QFQ pilot first.")
        return 1

    checked = 0
    total_completed = 0
    total_forming = 0
    best: list[tuple[float, str, str, str, int]] = []

    for symbol in symbols[:8]:
        try:
            result = service.analyze(
                symbol,
                bars=1200,
                scales=(2, 3, 5, 8, 13, 21),
                max_completed=60,
                max_forming=60,
            )
        except DatasetNotFoundError:
            print(f"[HT-CN M2 LOCAL] SKIP {symbol}: base dataset missing")
            continue

        if not result["price_mode"].startswith("qfq"):
            print(f"[HT-CN M2 LOCAL] FAIL {symbol}: expected QFQ view, got {result['price_mode']}")
            return 1
        if int(result["bars_returned"]) < 80:
            print(f"[HT-CN M2 LOCAL] FAIL {symbol}: only {result['bars_returned']} bars")
            return 1

        completed = result["completed"]
        forming = result["forming"]
        for pattern in [*completed, *forming]:
            _assert_finite_pattern(pattern)
            best.append(
                (
                    float(pattern["geometry_score"]),
                    symbol,
                    str(pattern["pattern_id"]),
                    str(pattern["state"]),
                    int(pattern["scale"]),
                )
            )

        checked += 1
        total_completed += len(completed)
        total_forming += len(forming)
        print(
            f"[HT-CN M2 LOCAL] {symbol}: mode={result['price_mode']}, bars={result['bars_returned']}, "
            f"completed={len(completed)}, forming={len(forming)}, pivots={result['pivot_counts']}"
        )
        if result["warning"]:
            print(f"[HT-CN M2 LOCAL] WARN {symbol}: {result['warning']}")

    if checked == 0:
        print("[HT-CN M2 LOCAL] FAIL: no QFQ symbol also has a local base dataset.")
        return 1

    print(
        f"[HT-CN M2 LOCAL] SUMMARY checked={checked}, completed={total_completed}, forming={total_forming}"
    )
    if best:
        print("[HT-CN M2 LOCAL] Top geometry candidates (score is not probability):")
        for score, symbol, pattern_id, state, scale in sorted(best, reverse=True)[:10]:
            print(f"  {symbol} {pattern_id} {state} S{scale} score={score:.2f}")
    else:
        print(
            "[HT-CN M2 LOCAL] NOTE: no source-valid pattern in the current pilot windows. "
            "This is a valid zero-result, not a reason to loosen Carney identity rules."
        )

    print("[HT-CN M2 LOCAL] PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
