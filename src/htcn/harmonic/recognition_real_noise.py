from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from itertools import pairwise

import pandas as pd

from .recognition_benchmark import RecognitionTruth
from .recognition_stress import STANDARD_XABCD

HOLDOUT_SALT = "htcn-recognition-gate3-holdout-v1"
NODE_INDICES = (20, 100, 180, 260, 340)
ROWS = 381


@dataclass(frozen=True, slots=True)
class SyntheticRealCase:
    instrument_id: str
    split: str
    seed: int
    pattern_id: str
    direction: str
    source_start: int
    source_end: int
    truth: RecognitionTruth
    frame: pd.DataFrame


def holdout_symbols(
    instrument_ids: list[str] | tuple[str, ...],
    *,
    count: int,
) -> tuple[str, ...]:
    if count < 1 or count >= len(instrument_ids):
        raise ValueError("holdout count must be between 1 and len(symbols)-1")
    ranked = sorted(
        {str(value) for value in instrument_ids},
        key=lambda value: hashlib.sha256(
            f"{HOLDOUT_SALT}:{value}".encode()
        ).hexdigest(),
    )
    return tuple(ranked[:count])


def _scaled_pattern(
    pattern_id: str,
    *,
    direction: str,
    center: float,
    xa_amplitude: float,
) -> tuple[float, ...]:
    source = STANDARD_XABCD[pattern_id]
    x0, a0 = source[0], source[1]
    denom = a0 - x0
    if denom == 0:
        raise ValueError("invalid canonical pattern")
    normalized = tuple((value - x0) / denom for value in source)
    sign = 1.0 if direction == "bullish" else -1.0
    return tuple(center + sign * xa_amplitude * value for value in normalized)


def _leg_residual(
    close: pd.Series,
    *,
    left: int,
    right: int,
) -> list[float]:
    segment = close.iloc[left : right + 1].astype(float).reset_index(drop=True)
    if len(segment) < 3:
        return [0.0] * len(segment)
    log_values = segment.map(lambda value: math.log(max(value, 1e-9)))
    returns = log_values.diff().fillna(0.0)
    lo = returns.quantile(0.05)
    hi = returns.quantile(0.95)
    clipped = returns.clip(lower=lo, upper=hi)
    cumulative = clipped.cumsum()
    start = float(cumulative.iloc[0])
    end = float(cumulative.iloc[-1])
    baseline = [
        start + (end - start) * index / (len(cumulative) - 1)
        for index in range(len(cumulative))
    ]
    residual = [
        float(value) - float(base)
        for value, base in zip(cumulative.tolist(), baseline, strict=True)
    ]
    scale = max((abs(value) for value in residual), default=0.0)
    if scale <= 1e-12:
        return [0.0] * len(residual)
    return [value / scale for value in residual]


def inject_pattern_into_real_background(
    background: pd.DataFrame,
    *,
    instrument_id: str,
    pattern_id: str,
    direction: str,
    seed: int,
    split: str,
    noise_strength: float = 0.08,
) -> SyntheticRealCase:
    if pattern_id not in STANDARD_XABCD:
        raise ValueError(f"unsupported pattern: {pattern_id}")
    if direction not in {"bullish", "bearish"}:
        raise ValueError("direction must be bullish or bearish")
    if len(background) < ROWS:
        raise ValueError(f"background requires at least {ROWS} rows")
    if noise_strength < 0 or noise_strength > 0.20:
        raise ValueError("noise_strength must be within [0, 0.20]")

    max_start = len(background) - ROWS
    source_start = seed % (max_start + 1)
    source_end = source_start + ROWS
    source = background.iloc[source_start:source_end].reset_index(drop=True).copy()

    median_close = float(source["close"].astype(float).median())
    median_range = float((source["high"].astype(float) - source["low"].astype(float)).median())
    xa_amplitude = min(
        median_close * 0.32,
        max(median_close * 0.14, median_range * 14.0),
    )
    prices = _scaled_pattern(
        pattern_id,
        direction=direction,
        center=median_close,
        xa_amplitude=xa_amplitude,
    )

    closes = [0.0] * ROWS
    source_close = source["close"].astype(float)
    anchors = [(0, prices[0] + (prices[0] - prices[1]) * 0.15)]
    anchors.extend(zip(NODE_INDICES, prices, strict=True))
    anchors.append((ROWS - 1, prices[-1] + (prices[-1] - prices[-2]) * 0.15))

    for (left_i, left_p), (right_i, right_p) in pairwise(anchors):
        residual = _leg_residual(source_close, left=left_i, right=right_i)
        leg = right_p - left_p
        for offset, index in enumerate(range(left_i, right_i + 1)):
            fraction = (index - left_i) / (right_i - left_i)
            ideal = left_p + leg * fraction
            taper = math.sin(math.pi * fraction)
            perturbation = (
                residual[offset]
                * abs(leg)
                * noise_strength
                * taper
            )
            closes[index] = ideal + perturbation

    for index, price in zip(NODE_INDICES, prices, strict=True):
        closes[index] = price

    open_rel = (
        (source["open"].astype(float) - source_close) / source_close.replace(0.0, float("nan"))
    ).fillna(0.0).clip(-0.04, 0.04)
    upper_rel = (
        (source["high"].astype(float) - source[["open", "close"]].astype(float).max(axis=1))
        / source_close.replace(0.0, float("nan"))
    ).fillna(0.0).clip(0.0, 0.05)
    lower_rel = (
        (source[["open", "close"]].astype(float).min(axis=1) - source["low"].astype(float))
        / source_close.replace(0.0, float("nan"))
    ).fillna(0.0).clip(0.0, 0.05)

    opens: list[float] = []
    highs: list[float] = []
    lows: list[float] = []
    for index, close_value in enumerate(closes):
        open_value = close_value * (1.0 + float(open_rel.iloc[index]))
        high_value = max(open_value, close_value) + close_value * float(upper_rel.iloc[index])
        low_value = min(open_value, close_value) - close_value * float(lower_rel.iloc[index])
        opens.append(open_value)
        highs.append(high_value)
        lows.append(max(1e-6, low_value))

    # Preserve exact structural extrema at the injected truth nodes. Real bar microstructure
    # remains everywhere else, but no wick is allowed to move the known major node itself.
    for position, node_index in enumerate(NODE_INDICES):
        price = prices[position]
        opens[node_index] = price
        highs[node_index] = price
        lows[node_index] = price

    # Interior wicks may create minor pivots, but cannot exceed either endpoint of their
    # containing major leg. This preserves known truth while retaining real local texture.
    for left_index, right_index in pairwise(NODE_INDICES):
        low_bound = min(closes[left_index], closes[right_index])
        high_bound = max(closes[left_index], closes[right_index])
        epsilon = max((high_bound - low_bound) * 1e-6, 1e-9)
        for index in range(left_index + 1, right_index):
            highs[index] = min(highs[index], high_bound - epsilon)
            lows[index] = max(lows[index], low_bound + epsilon)
            opens[index] = min(max(opens[index], lows[index]), highs[index])
            closes[index] = min(max(closes[index], lows[index]), highs[index])

    result = pd.DataFrame(
        {
            "open": opens,
            "high": highs,
            "low": lows,
            "close": closes,
            "volume": source["volume"].astype(float).tolist(),
        }
    )
    truth = RecognitionTruth(
        case_id=f"real_noise:{instrument_id}:{pattern_id}:{direction}:s{seed}",
        pattern_id=pattern_id,
        direction=direction,
        labels=("X", "A", "B", "C", "D"),
        node_indices=NODE_INDICES,
    )
    return SyntheticRealCase(
        instrument_id=instrument_id,
        split=split,
        seed=seed,
        pattern_id=pattern_id,
        direction=direction,
        source_start=source_start,
        source_end=source_end,
        truth=truth,
        frame=result,
    )
