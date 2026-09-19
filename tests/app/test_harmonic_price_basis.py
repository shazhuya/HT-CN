from __future__ import annotations

import pandas as pd

from htcn.app.harmonic_service import LocalHarmonicService


def _factors(rows: list[tuple[str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "instrument_id": ["SSE.600000"] * len(rows),
            "trade_date": [pd.Timestamp(day) for day, _ in rows],
            "price_factor": [factor for _, factor in rows],
            "mode": ["qfq"] * len(rows),
            "source": ["test"] * len(rows),
        }
    )


def test_qfq_basis_id_ignores_same_factor_date_extension() -> None:
    first = _factors([
        ("2026-09-17", 1.0),
        ("2026-09-18", 1.0),
    ])
    extended = _factors([
        ("2026-09-17", 1.0),
        ("2026-09-18", 1.0),
        ("2026-09-21", 1.0),
    ])
    assert LocalHarmonicService._qfq_basis_id(first) == (
        LocalHarmonicService._qfq_basis_id(extended)
    )


def test_qfq_basis_id_changes_on_new_factor_regime() -> None:
    before = _factors([
        ("2026-09-17", 1.0),
        ("2026-09-18", 1.0),
    ])
    after = _factors([
        ("2026-09-17", 1.0),
        ("2026-09-18", 1.0),
        ("2026-09-21", 0.93),
    ])
    assert LocalHarmonicService._qfq_basis_id(before) != (
        LocalHarmonicService._qfq_basis_id(after)
    )


def test_qfq_basis_id_is_deterministic_under_row_reordering() -> None:
    factors = _factors([
        ("2026-09-17", 1.0),
        ("2026-09-18", 0.95),
        ("2026-09-21", 0.95),
    ])
    reversed_rows = factors.iloc[::-1].reset_index(drop=True)
    first = LocalHarmonicService._qfq_basis_id(factors)
    second = LocalHarmonicService._qfq_basis_id(reversed_rows)
    assert first == second
    assert first.startswith("qfq:")
    assert len(first) == 68
