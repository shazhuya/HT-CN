from __future__ import annotations

import math

import pandas as pd


def wilder_rsi(close: pd.Series, *, period: int = 14) -> pd.Series:
    """Return Wilder RSI using the original recursive average.

    Harmonic Trading Volume Three uses Wilder RSI as one of the primary confirmation
    measures and explicitly references the conventional 14-period formulation with
    30/70 extreme zones.  HT-CN keeps this primitive separate from pattern identity:
    RSI may confirm or contextualize a completed pattern, but it can never create or
    alter X/A/B/C/D geometry.
    """

    if period < 2:
        raise ValueError("RSI period must be >= 2")

    values = pd.to_numeric(close, errors="coerce").astype(float)
    out = pd.Series(float("nan"), index=values.index, dtype="float64")
    if len(values) <= period:
        return out

    delta = values.diff()
    gains = delta.clip(lower=0.0)
    losses = (-delta.clip(upper=0.0))

    seed_gain = gains.iloc[1 : period + 1]
    seed_loss = losses.iloc[1 : period + 1]
    if seed_gain.isna().any() or seed_loss.isna().any():
        return out

    avg_gain = float(seed_gain.mean())
    avg_loss = float(seed_loss.mean())

    def rsi_value(gain: float, loss: float) -> float:
        if not math.isfinite(gain) or not math.isfinite(loss):
            return float("nan")
        if loss == 0.0:
            return 50.0 if gain == 0.0 else 100.0
        rs = gain / loss
        return 100.0 - (100.0 / (1.0 + rs))

    out.iloc[period] = rsi_value(avg_gain, avg_loss)

    for i in range(period + 1, len(values)):
        gain = float(gains.iloc[i])
        loss = float(losses.iloc[i])
        if not math.isfinite(gain) or not math.isfinite(loss):
            out.iloc[i] = float("nan")
            continue
        avg_gain = ((avg_gain * (period - 1)) + gain) / period
        avg_loss = ((avg_loss * (period - 1)) + loss) / period
        out.iloc[i] = rsi_value(avg_gain, avg_loss)

    return out
