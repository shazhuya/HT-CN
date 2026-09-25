from __future__ import annotations

import hashlib
import json
import random
from dataclasses import dataclass
from itertools import pairwise
from typing import Literal

import pandas as pd

from .recognition_benchmark import RecognitionTruth


STANDARD_XABCD: dict[str, tuple[float, ...]] = {
    "gartley": (100.0, 200.0, 138.2, 183.2, 121.4),
    "bat": (100.0, 200.0, 150.0, 188.6, 111.4),
    "butterfly": (100.0, 200.0, 121.4, 169.8, 73.0),
    "crab": (100.0, 200.0, 150.0, 194.3, 38.2),
    "deep_crab": (100.0, 200.0, 111.4, 156.6410383189, 38.2),
}

LEG_NAMES = ("XA", "AB", "BC", "CD")
NegativeKind = Literal["invalid_b", "invalid_c", "invalid_d"]


@dataclass(frozen=True, slots=True)
class PositiveStressCase:
    truth: RecognitionTruth
    frame: pd.DataFrame
    seed: int
    contaminated_legs: tuple[str, ...]
    minor_pairs: int


@dataclass(frozen=True, slots=True)
class NegativeStressCase:
    case_id: str
    frame: pd.DataFrame
    kind: NegativeKind
    seed: int


def _mirror(prices: tuple[float, ...], *, axis: float = 300.0) -> tuple[float, ...]:
    return tuple(axis - value for value in prices)


def _render_path(anchors: list[tuple[int, float]], *, rows: int) -> pd.DataFrame:
    closes = [0.0] * rows
    for (left_i, left_p), (right_i, right_p) in pairwise(anchors):
        if right_i <= left_i:
            raise ValueError("anchor indices must increase")
        for index in range(left_i, right_i + 1):
            fraction = (index - left_i) / (right_i - left_i)
            closes[index] = left_p + (right_p - left_p) * fraction
    return pd.DataFrame(
        {
            "open": closes,
            "high": closes,
            "low": closes,
            "close": closes,
            "volume": [1000.0] * rows,
        }
    )


def _oriented_prices(
    prices: tuple[float, ...],
    direction: str,
) -> tuple[float, ...]:
    if direction == "bullish":
        return prices
    if direction == "bearish":
        return _mirror(prices)
    raise ValueError(f"unsupported direction: {direction}")


def _minor_pair(
    *,
    left_i: int,
    right_i: int,
    left_p: float,
    right_p: float,
    rng: random.Random,
) -> tuple[tuple[int, float], tuple[int, float]]:
    span_bars = right_i - left_i
    span_price = abs(right_p - left_p)
    if span_bars < 24:
        raise ValueError("stress leg too short for a confirmed minor pair")

    first_fraction = rng.uniform(0.28, 0.48)
    second_fraction = rng.uniform(0.16, first_fraction - 0.07)
    first_t = rng.uniform(0.30, 0.43)
    second_t = rng.uniform(0.56, 0.70)
    first_i = left_i + max(6, int(round(span_bars * first_t)))
    second_i = left_i + max(first_i - left_i + 6, int(round(span_bars * second_t)))
    second_i = min(second_i, right_i - 6)

    direction = 1.0 if right_p > left_p else -1.0
    first_p = left_p + direction * span_price * first_fraction
    second_p = left_p + direction * span_price * second_fraction
    return (first_i, first_p), (second_i, second_p)


def render_random_contaminated_xabcd(
    prices: tuple[float, ...],
    *,
    direction: str,
    seed: int,
    contaminated_legs: tuple[str, ...],
) -> tuple[pd.DataFrame, tuple[int, ...]]:
    rng = random.Random(seed)
    oriented = _oriented_prices(prices, direction)
    labels = ("X", "A", "B", "C", "D")
    node_indices = (30, 110, 190, 270, 350)
    points = dict(zip(labels, oriented, strict=True))
    indices = dict(zip(labels, node_indices, strict=True))

    x, a, _, c, d = oriented
    first_guard = x + (1.0 if a > x else -1.0) * abs(a - x) * 0.18
    last_guard = d - (1.0 if d > c else -1.0) * abs(d - c) * 0.18
    anchors: list[tuple[int, float]] = [(0, first_guard), (node_indices[0], x)]

    for leg_name, left_label, right_label in zip(
        LEG_NAMES,
        labels[:-1],
        labels[1:],
        strict=True,
    ):
        left_i = indices[left_label]
        right_i = indices[right_label]
        left_p = points[left_label]
        right_p = points[right_label]
        if leg_name in contaminated_legs:
            anchors.extend(
                _minor_pair(
                    left_i=left_i,
                    right_i=right_i,
                    left_p=left_p,
                    right_p=right_p,
                    rng=rng,
                )
            )
        anchors.append((right_i, right_p))

    anchors.append((390, last_guard))
    return _render_path(anchors, rows=391), node_indices


def positive_stress_cases(
    *,
    seeds_per_depth: int = 4,
) -> tuple[PositiveStressCase, ...]:
    if seeds_per_depth < 1:
        raise ValueError("seeds_per_depth must be positive")

    cases: list[PositiveStressCase] = []
    for pattern_index, (pattern_id, prices) in enumerate(STANDARD_XABCD.items()):
        for direction_index, direction in enumerate(("bullish", "bearish")):
            for depth in (1, 2, 3):
                for local_seed in range(seeds_per_depth):
                    seed = (
                        10_000 * (pattern_index + 1)
                        + 1_000 * direction_index
                        + 100 * depth
                        + local_seed
                    )
                    rng = random.Random(seed)
                    contaminated_legs = tuple(
                        sorted(rng.sample(list(LEG_NAMES), k=depth))
                    )
                    frame, indices = render_random_contaminated_xabcd(
                        prices,
                        direction=direction,
                        seed=seed,
                        contaminated_legs=contaminated_legs,
                    )
                    cases.append(
                        PositiveStressCase(
                            truth=RecognitionTruth(
                                case_id=(
                                    f"random_minor:d{depth}:s{seed}:"
                                    f"{pattern_id}:{direction}"
                                ),
                                pattern_id=pattern_id,
                                direction=direction,
                                labels=("X", "A", "B", "C", "D"),
                                node_indices=indices,
                            ),
                            frame=frame,
                            seed=seed,
                            contaminated_legs=contaminated_legs,
                            minor_pairs=depth,
                        )
                    )
    return tuple(cases)


def _clean_negative_prices(
    *,
    base_pattern: str,
    kind: NegativeKind,
) -> tuple[float, ...]:
    x, a, b, c, d = STANDARD_XABCD[base_pattern]
    xa = a - x

    if kind == "invalid_b":
        # B/XA = 0.70: outside every executable standard XABCD B identity/tolerance.
        b = a - xa * 0.70
        # Keep C as a harmonic 0.618 retracement of the mutated AB leg.
        c = b - (b - a) * 0.618
    elif kind == "invalid_c":
        # C/AB = 0.66: deliberately between 0.618 and 0.707 and outside 3% family tolerance.
        c = b - (b - a) * 0.66
    elif kind == "invalid_d":
        # D/XA = 1.00: outside Gartley/Bat/Butterfly/Crab/Deep-Crab completion ratios.
        d = a - xa * 1.00
    else:
        raise ValueError(f"unsupported negative kind: {kind}")
    return (x, a, b, c, d)


def negative_stress_cases(
    *,
    copies_per_kind: int = 10,
) -> tuple[NegativeStressCase, ...]:
    if copies_per_kind < 1:
        raise ValueError("copies_per_kind must be positive")

    cases: list[NegativeStressCase] = []
    base_patterns = tuple(STANDARD_XABCD)
    for kind_index, kind in enumerate(("invalid_b", "invalid_c", "invalid_d")):
        for copy_index in range(copies_per_kind):
            base_pattern = base_patterns[copy_index % len(base_patterns)]
            seed = 70_000 + kind_index * 1_000 + copy_index
            direction = "bullish" if copy_index % 2 == 0 else "bearish"
            prices = _clean_negative_prices(base_pattern=base_pattern, kind=kind)
            frame, _ = render_random_contaminated_xabcd(
                prices,
                direction=direction,
                seed=seed,
                contaminated_legs=(),
            )
            cases.append(
                NegativeStressCase(
                    case_id=(
                        f"near_miss:{kind}:s{seed}:{base_pattern}:{direction}"
                    ),
                    frame=frame,
                    kind=kind,
                    seed=seed,
                )
            )
    return tuple(cases)


def append_future_replacement_tail(
    frame: pd.DataFrame,
    truth: RecognitionTruth,
) -> pd.DataFrame:
    """Append a deterministic same-kind replacement after D without changing the prefix."""

    if truth.labels != ("X", "A", "B", "C", "D"):
        raise ValueError("future-tail fixture requires X/A/B/C/D truth")
    d_index = truth.node_indices[-1]
    if d_index >= len(frame):
        raise ValueError("truth D must exist inside the source frame")

    closes = frame["close"].astype(float).tolist()
    d_price = float(closes[d_index])
    c_price = float(closes[truth.node_indices[-2]])
    direction = truth.direction
    rebound = abs(c_price - d_price) * 0.12
    replacement = abs(c_price - d_price) * 0.08

    prefix_end = min(len(closes) - 1, d_index + 12)
    base = closes[: prefix_end + 1]
    start = float(base[-1])
    if direction == "bullish":
        tail_anchors = [
            (0, start),
            (8, d_price + rebound),
            (16, d_price - replacement),
            (24, d_price + rebound * 0.8),
        ]
    else:
        tail_anchors = [
            (0, start),
            (8, d_price - rebound),
            (16, d_price + replacement),
            (24, d_price - rebound * 0.8),
        ]
    tail = _render_path(tail_anchors, rows=25)
    tail = tail.iloc[1:].reset_index(drop=True)
    prefix = frame.iloc[: prefix_end + 1].reset_index(drop=True)
    return pd.concat([prefix, tail], ignore_index=True)


def corpus_fingerprint(
    positives: tuple[PositiveStressCase, ...],
    negatives: tuple[NegativeStressCase, ...],
) -> str:
    payload = []
    for case in positives:
        payload.append(
            {
                "kind": "positive",
                "truth": {
                    "case_id": case.truth.case_id,
                    "pattern_id": case.truth.pattern_id,
                    "direction": case.truth.direction,
                    "labels": case.truth.labels,
                    "node_indices": case.truth.node_indices,
                },
                "seed": case.seed,
                "contaminated_legs": case.contaminated_legs,
                "ohlc": case.frame[["open", "high", "low", "close"]]
                .round(10)
                .values.tolist(),
            }
        )
    for case in negatives:
        payload.append(
            {
                "kind": case.kind,
                "case_id": case.case_id,
                "seed": case.seed,
                "ohlc": case.frame[["open", "high", "low", "close"]]
                .round(10)
                .values.tolist(),
            }
        )
    material = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()
