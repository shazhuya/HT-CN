from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from itertools import pairwise
from math import floor, isfinite

import pandas as pd

PINE_R34_SOURCE_SHA256 = "84e1eb2267c9b80891e0ffb64a6d4abf5712fc5e756be81815e536f2fca4c3f5"
PINE_R34_SCALES: tuple[int, ...] = (5, 10, 20)
PINE_R34_NEAR_ATR = 1.5
PINE_R34_JOURNEY_ATR = 3.0
PINE_R34_NEAR_PCT = 12.0
PINE_R34_JOURNEY_PCT = 25.0
PINE_R34_VISIBLE_WIDTH_ATR = 2.0
PINE_R34_DEVELOPING_AGE = 180
PINE_R34_FRESH_BARS = 5
PINE_R34_CANDIDATE_TABLE_LIMIT = 12
PINE_R34_UNQUALIFIED_STORAGE_LIMIT = 30
DISCRETE_PROJECTIONS: tuple[float, ...] = (
    1.0,
    1.13,
    1.27,
    1.414,
    1.618,
    2.0,
    2.24,
    2.618,
    3.14,
    3.618,
)
ABCD_C_TARGETS: tuple[float, ...] = (0.382, 0.50, 0.618, 0.707, 0.786, 0.886)
ABCD_BC_TARGETS: tuple[float, ...] = (2.618, 2.0, 1.618, 1.414, 1.272, 1.13)

_PATTERN_NAMES = {
    0: "gartley",
    1: "bat",
    2: "alternate_bat",
    3: "butterfly",
    4: "crab",
    5: "deep_crab",
    6: "shark",
    7: "five_zero",
    8: "abcd",
    9: "abcd_127",
    10: "abcd_1618",
    11: "deep_gartley",
}

_PATTERN_SCHEMA = {
    0: "XABCD",
    1: "XABCD",
    2: "XABCD",
    3: "XABCD",
    4: "XABCD",
    5: "XABCD",
    6: "0XABC",
    7: "0XABCD",
    8: "ABCD",
    9: "ABCD",
    10: "ABCD",
    11: "XABCD",
}

_SOURCE_LABELS = {
    0: ("X", "A", "B", "C"),
    1: ("X", "A", "B", "C"),
    2: ("X", "A", "B", "C"),
    3: ("X", "A", "B", "C"),
    4: ("X", "A", "B", "C"),
    5: ("X", "A", "B", "C"),
    6: ("0", "X", "A", "B"),
    7: ("0", "X", "A", "B", "C"),
    8: ("A", "B", "C"),
    9: ("A", "B", "C"),
    10: ("A", "B", "C"),
    11: ("X", "A", "B", "C"),
}

_SOURCE_COUNT = {rule: len(labels) for rule, labels in _SOURCE_LABELS.items()}


@dataclass(frozen=True, slots=True)
class PineR34Pivot:
    index: int
    price: float
    kind: int
    scale: int
    confirmed_at: int

    def __post_init__(self) -> None:
        if self.kind not in (-1, 1):
            raise ValueError("kind must be -1 or 1")
        if self.index < 0 or self.confirmed_at < self.index:
            raise ValueError("invalid pivot timing")


@dataclass(slots=True)
class PineR34Candidate:
    candidate_id: int
    rule: int
    pattern_id: str
    schema: str
    direction: int
    scale: int
    source_nodes: tuple[PineR34Pivot, ...]
    source_labels: tuple[str, ...]
    m1: float
    m2: float
    m3: float
    prz_low: float
    prz_high: float
    structural_limit: float
    reference_scale: float
    atr_at_birth: float
    born_bar: int
    expires_bar: int
    qualified: bool
    precise: bool
    research_only: bool
    quality_reason: str
    c_ideal: float | None = None
    bc_ideal: float | None = None
    c_error: float | None = None
    convergence_error: float | None = None
    live: bool = True
    closed_bar: int | None = None
    close_reason: str | None = None
    first_test_bar: int | None = None
    test_count: int = 0
    coverage_mask: int = 0
    test_start_bar: int | None = None
    test_last_bar: int | None = None
    test_atr: float | None = None
    session_resets: int = 0
    current_distance_atr: float | None = None
    current_distance_pct: float | None = None
    source_age: int | None = None
    observable: bool = False
    monitoring_rank: float | None = None
    recently_tested: bool = False

    @property
    def conflict_key(self) -> tuple[int, ...]:
        return tuple(node.index for node in self.source_nodes)

    @property
    def projected_label(self) -> str:
        return "C" if self.rule == 6 else "D"

    @property
    def source_known_at(self) -> int:
        return self.born_bar

    def as_payload(self) -> dict[str, object]:
        return {
            "candidate_id": self.candidate_id,
            "pattern_id": self.pattern_id,
            "schema": self.schema,
            "direction": "bullish" if self.direction == 1 else "bearish",
            "scale": self.scale,
            "source_nodes": [
                {
                    "label": label,
                    "index": node.index,
                    "price": node.price,
                    "kind": "high" if node.kind == 1 else "low",
                    "confirmed_at": node.confirmed_at,
                }
                for label, node in zip(self.source_labels, self.source_nodes, strict=True)
            ],
            "measurements": {
                "m1": self.m1,
                "m2": self.m2,
                "m3": self.m3,
                "prz_low": self.prz_low,
                "prz_high": self.prz_high,
                "structural_limit": self.structural_limit,
            },
            "projected_label": self.projected_label,
            "born_bar": self.born_bar,
            "expires_bar": self.expires_bar,
            "live": self.live,
            "closed_bar": self.closed_bar,
            "close_reason": self.close_reason,
            "qualified": self.qualified,
            "precise": self.precise,
            "research_only": self.research_only,
            "quality_reason": self.quality_reason,
            "first_test_bar": self.first_test_bar,
            "test_count": self.test_count,
            "current_distance_atr": self.current_distance_atr,
            "current_distance_pct": self.current_distance_pct,
            "source_age": self.source_age,
            "observable": self.observable,
            "monitoring_rank": self.monitoring_rank,
            "recently_tested": self.recently_tested,
            "source": "pine_r34",
            "pine_source_sha256": PINE_R34_SOURCE_SHA256,
        }


@dataclass(frozen=True, slots=True)
class PineR34Scan:
    candidates: tuple[PineR34Candidate, ...]
    live_candidates: tuple[PineR34Candidate, ...]
    monitoring_candidates: tuple[PineR34Candidate, ...]
    pivots_by_scale: dict[int, tuple[PineR34Pivot, ...]]
    diagnostics: dict[str, object]


@dataclass(frozen=True, slots=True)
class _Geometry:
    ok: bool
    direction: int
    m1: float | None
    m2: float | None
    m3: float | None
    low: float | None
    high: float | None
    limit: float | None
    reference_scale: float | None
    reason: str
    qualified: bool = True
    precise: bool = True
    quality_reason: str = "形态比例通过"
    c_ideal: float | None = None
    bc_ideal: float | None = None
    c_error: float | None = None
    convergence_error: float | None = None


def _validate_frame(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"open", "high", "low", "close"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing Pine R3.4 columns: {sorted(missing)}")
    if frame.empty:
        return frame.copy()
    out = frame.copy().reset_index(drop=True)
    for column in ("open", "high", "low", "close"):
        out[column] = pd.to_numeric(out[column], errors="raise").astype(float)
    if out[list(required)].isnull().any().any():
        raise ValueError("Pine R3.4 source contains null OHLC")
    if (out["high"] < out["low"]).any():
        raise ValueError("Pine R3.4 source contains high < low")
    return out


def _rma(values: list[float], length: int) -> list[float | None]:
    out: list[float | None] = [None] * len(values)
    if length < 1 or len(values) < length:
        return out
    seed = sum(values[:length]) / float(length)
    out[length - 1] = seed
    prior = seed
    alpha = 1.0 / float(length)
    for index in range(length, len(values)):
        prior = alpha * values[index] + (1.0 - alpha) * prior
        out[index] = prior
    return out


def pine_atr(frame: pd.DataFrame, length: int = 14) -> tuple[float | None, ...]:
    source = _validate_frame(frame)
    if source.empty:
        return ()
    tr: list[float] = []
    previous_close: float | None = None
    for row in source.itertuples(index=False):
        high = float(row.high)
        low = float(row.low)
        if previous_close is None:
            value = high - low
        else:
            value = max(high - low, abs(high - previous_close), abs(low - previous_close))
        tr.append(value)
        previous_close = float(row.close)
    return tuple(_rma(tr, length))


def _strict_pivot(
    highs: list[float],
    lows: list[float],
    *,
    confirmation_bar: int,
    strength: int,
    scale: int,
) -> PineR34Pivot | None:
    center = confirmation_bar - strength
    if center - strength < 0 or center + strength >= len(highs):
        return None
    high_window = highs[center - strength : center + strength + 1]
    low_window = lows[center - strength : center + strength + 1]
    center_high = highs[center]
    center_low = lows[center]
    is_high = center_high == max(high_window) and high_window.count(center_high) == 1
    is_low = center_low == min(low_window) and low_window.count(center_low) == 1
    # Pine source deliberately refuses an ambiguous same-confirmation high+low.
    if is_high == is_low:
        return None
    return PineR34Pivot(
        index=center,
        price=float(center_high if is_high else center_low),
        kind=1 if is_high else -1,
        scale=scale,
        confirmed_at=confirmation_bar,
    )


def _feed(stream: list[PineR34Pivot], pivot: PineR34Pivot | None) -> bool:
    if pivot is None:
        return False
    if not stream:
        stream.append(pivot)
        return True
    last = stream[-1]
    if pivot.index <= last.index:
        return False
    if pivot.kind != last.kind:
        stream.append(pivot)
        changed = True
    else:
        more_extreme = pivot.price > last.price if pivot.kind == 1 else pivot.price < last.price
        if not more_extreme:
            return False
        stream[-1] = pivot
        changed = True
    if len(stream) > 14:
        stream.pop(0)
    return changed


def _between(value: float, low: float, high: float) -> bool:
    return isfinite(value) and value >= low - 1e-9 and value <= high + 1e-9


def _fixed(value: float, target: float, tolerance: float) -> bool:
    return target > 0 and isfinite(value) and abs(value / target - 1.0) <= tolerance + 1e-9


def _ratio(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator > 0 else float("nan")


def _nearest(
    origin: float,
    direction: int,
    leg: float,
    core: float,
    low: float,
    high: float,
) -> float | None:
    best: float | None = None
    gap = float("inf")
    for ratio in DISCRETE_PROJECTIONS:
        if not _between(ratio, low, high):
            continue
        price = origin - direction * leg * ratio
        distance = abs(price - core)
        if distance < gap:
            best = price
            gap = distance
    return best


def _abcd_pair(ratio: float) -> tuple[float, float, float]:
    rows = [
        (c, bc, abs(ratio / c - 1.0))
        for c, bc in zip(ABCD_C_TARGETS, ABCD_BC_TARGETS, strict=True)
    ]
    return min(rows, key=lambda row: row[2])


def _tick_price(price: float, tick: float) -> float:
    if tick <= 0:
        raise ValueError("tick must be positive")
    # Positive A-share prices: Pine math.round semantics are half-away/up here.
    return floor(price / tick + 0.5) * tick


def _geometry(
    rule: int,
    nodes: tuple[PineR34Pivot, ...],
    *,
    atr: float,
    tick: float,
    min_leg_atr: float,
    max_bars: int,
    cluster_width: float,
    abcd_tolerance_pct: float,
    abcd_convergence_pct: float,
) -> _Geometry:
    direction = nodes[-1].kind
    ok = atr > 0
    reason = "前置比例/拓扑不符"
    for left, right in pairwise(nodes):
        ok = (
            ok
            and right.index > left.index
            and left.kind != right.kind
            and abs(right.price - left.price) >= max(tick, atr * min_leg_atr)
        )
    ok = ok and nodes[-1].index - nodes[0].index <= max_bars
    m1 = m2 = m3 = limit = reference = None

    if rule == 6:
        zero, x, a, b = (node.price for node in nodes)
        ox = abs(x - zero)
        xa = abs(a - x)
        ab = abs(b - a)
        ob = abs(b - zero)
        ok = (
            ok
            and ox > 0
            and xa > 0
            and ob > 0
            and direction * (x - a) > 0
            and direction * (a - zero) > 0
            and direction * (b - x) > 0
            and _between(_ratio(xa, ox), 0.382, 0.618)
            and _between(_ratio(ab, xa), 1.13, 1.618)
        )
        m1 = b - direction * ob * 0.886
        m2 = _nearest(b, direction, ab, m1, 1.618, 2.24)
        m3 = m1
        limit = b - direction * ob * 1.13
        reference = ob
    elif rule == 7:
        zero, x, a, b, c = (node.price for node in nodes)
        xa = abs(a - x)
        ab = abs(b - a)
        bc = abs(c - b)
        ok = (
            ok
            and xa > 0
            and ab > 0
            and direction * (zero - a) > 0
            and direction * (a - x) > 0
            and direction * (x - b) > 0
            and direction * (c - a) > 0
            and _between(_ratio(ab, xa), 1.13, 1.618)
            and _between(_ratio(bc, ab), 1.618, 2.24)
        )
        m1 = c - direction * bc * 0.5
        m2 = c - direction * ab
        m3 = m1
        limit = b
        reference = bc
    elif rule in (8, 9, 10):
        a, b, c = (node.price for node in nodes)
        ab = abs(a - b)
        bc = abs(c - b)
        projection = 1.0 if rule == 8 else 1.27 if rule == 9 else 1.618
        ok = (
            ok
            and ab > 0
            and bc > 0
            and direction * (a - c) > 0
            and direction * (c - b) > 0
            and _between(_ratio(bc, ab), 0.382, 0.886)
        )
        m1 = c - direction * ab * projection
        m2 = m1
        m3 = m1
        limit_ratio = 1.27 if rule == 8 else 1.618 if rule == 9 else 2.0
        limit = c - direction * ab * limit_ratio
        reference = ab
    else:
        x, a, b, c = (node.price for node in nodes)
        xa = abs(a - x)
        ab = abs(b - a)
        bc = abs(c - b)
        br = _ratio(ab, xa)
        if rule in (0, 11):
            b_ok = _fixed(br, 0.618, 0.03)
        elif rule == 3:
            b_ok = _fixed(br, 0.786, 0.03)
        elif rule == 5:
            b_ok = _between(br, 0.886, 0.886 * 1.05)
        elif rule == 1:
            b_ok = _between(br, 0.382, 0.50 * 1.05)
        elif rule == 2:
            b_ok = _between(br, 0.01, 0.382)
        else:
            b_ok = _between(br, 0.382, 0.618)
        ok = (
            ok
            and xa > 0
            and ab > 0
            and bc > 0
            and direction * (a - x) > 0
            and direction * (b - x) > 0
            and direction * (a - c) > 0
            and direction * (c - b) > 0
            and b_ok
            and _between(_ratio(bc, ab), 0.382, 0.886)
        )
        d_ratio = 0.786 if rule == 0 else 0.886 if rule in (1, 11) else 1.13 if rule == 2 else 1.27 if rule == 3 else 1.618
        cb_low = 1.13 if rule == 0 else 2.0 if rule in (2, 5) else 2.618 if rule == 4 else 1.618
        cb_high = 1.618 if rule == 0 else 2.24 if rule == 3 else 2.618 if rule in (1, 11) else 3.618
        ab_low = 1.618 if rule == 2 else 1.0
        ab_high = 1.27 if rule in (0, 3) else 1.0 if rule == 11 else 1.618
        m1 = a - direction * xa * d_ratio
        m2 = m1 if rule in (2, 4) else _nearest(c, direction, ab, m1, ab_low, ab_high)
        if rule in (2, 4):
            projected = _ratio(direction * (c - m1), ab)
            ok = ok and projected >= (1.618 if rule == 2 else 1.0)
        m3 = _nearest(c, direction, bc, m1, cb_low, cb_high)
        limit_ratio = 1.0 if rule == 0 else 1.13 if rule in (1, 11) else 1.27 if rule == 2 else 1.414 if rule == 3 else 2.0
        limit = a - direction * xa * limit_ratio
        reference = xa
        if rule == 11 and m2 is not None:
            ok = ok and direction * (a - direction * xa * 0.786 - m2) > 0

    values = (m1, m2, m3, limit, reference)
    if any(value is None or not isfinite(float(value)) for value in values):
        return _Geometry(False, direction, m1, m2, m3, None, None, limit, reference, reason)
    assert m1 is not None and m2 is not None and m3 is not None
    assert limit is not None and reference is not None

    low = min(m1, m2, m3)
    high = max(m1, m2, m3)
    geometry_ok = ok
    compact = high - low <= reference * cluster_width
    boundary = low > limit if direction == 1 else high < limit
    source_price = nodes[-1].price
    pre_completion = direction * (source_price - (high if direction == 1 else low)) > 0
    ok = ok and compact and boundary and low > 0 and pre_completion
    if not geometry_ok:
        reason = "前置比例/拓扑不符"
    elif not compact:
        reason = "允许组合不汇聚（ENG宽度）"
    elif not boundary:
        reason = "测量超过结构极限"
    elif not ok:
        reason = "完成方向/价格无效"
    else:
        reason = "通过"

    qualified = True
    precise = True
    quality_reason = "形态比例通过"
    c_ideal = bc_ideal = c_error = convergence = None

    if ok and rule == 8:
        a, b, c = (node.price for node in nodes)
        ab = abs(a - b)
        bc = abs(c - b)
        c_ideal, bc_ideal, c_error = _abcd_pair(_ratio(bc, ab))
        convergence = abs(ab - bc * bc_ideal) / ab if ab > 0 else float("inf")
        precise = (
            ab > 0
            and bc > 0
            and c_error * 100.0 <= abcd_tolerance_pct + 1e-9
            and convergence * 100.0 <= abcd_convergence_pct + 1e-9
        )
        m2 = c - direction * bc * bc_ideal if precise else m1
        m3 = m1
        low = min(m1, m2)
        high = max(m1, m2)
        qualified = low > limit if direction == 1 else high < limit
        quality_reason = (
            "精准配对通过；相关测量不是独立胜率证据"
            if precise
            else "C在连续有效范围；未达精准配对，仅反应观察"
        )
    elif ok and rule in (9, 10):
        qualified = False
        quality_reason = "扩展ABCD独立投影：研究参考，不单独生成参与事件"

    return _Geometry(
        ok=bool(ok),
        direction=direction,
        m1=m1,
        m2=m2,
        m3=m3,
        low=low,
        high=high,
        limit=limit,
        reference_scale=reference,
        reason=reason,
        qualified=qualified,
        precise=precise,
        quality_reason=quality_reason,
        c_ideal=c_ideal,
        bc_ideal=bc_ideal,
        c_error=c_error,
        convergence_error=convergence,
    )


def _coverage(mask: int, low: float, high: float, m1: float, m2: float, m3: float, tick: float) -> int:
    epsilon = tick * 0.000001
    result = mask
    for bit, level in ((1, m1), (2, m2), (4, m3)):
        if low <= level + epsilon and high >= level - epsilon and result & bit == 0:
            result |= bit
    return result


def _distance(price: float, low: float, high: float) -> float:
    if price < low:
        return low - price
    if price > high:
        return price - high
    return 0.0


def _tier(
    price: float,
    low: float,
    high: float,
    atr: float,
    *,
    near_atr: float = PINE_R34_NEAR_ATR,
    journey_atr: float = PINE_R34_JOURNEY_ATR,
    near_pct: float = PINE_R34_NEAR_PCT,
    journey_pct: float = PINE_R34_JOURNEY_PCT,
) -> int:
    if atr <= 0 or price <= 0:
        return 2
    distance = _distance(price, low, high)
    distance_atr = distance / atr
    distance_pct = distance / price * 100.0
    if distance_atr <= near_atr and distance_pct <= near_pct:
        return 0
    if distance_atr <= journey_atr and distance_pct <= journey_pct:
        return 1
    return 2


def _observable(
    price: float,
    low: float,
    high: float,
    atr: float,
    *,
    visible_width_atr: float = PINE_R34_VISIBLE_WIDTH_ATR,
) -> bool:
    return (
        _tier(price, low, high, atr) <= 1
        and low > 0
        and high >= low
        and atr > 0
        and high - low <= atr * visible_width_atr
    )


def _candidate_rank(
    *,
    near_enough: bool,
    active_event: bool,
    rule: int,
    source_age: int,
    distance_atr: float,
) -> float:
    return (
        (100000.0 if active_event else 0.0)
        + (20000.0 if near_enough else 0.0)
        + (0.0 if 8 <= rule <= 10 else 20.0)
        - min(source_age, 2000) * 2.0
        - min(distance_atr, 500.0) * 40.0
    )


def _candidate_visible(
    *,
    live: bool,
    near_enough: bool,
    developing: bool,
    age: int,
    max_age: int,
    research: bool,
) -> bool:
    return live and (near_enough or (developing and age <= max_age) or research)


def _research_only(rule: int, qualified: bool, precise: bool) -> bool:
    # R3.4 may qualify these behaviorally; HT-CN keeps unresolved Source families non-authoritative.
    if rule in (2, 7, 9, 10, 11):
        return True
    if rule == 8 and (not qualified or not precise):
        return True
    return not qualified


def _candidate_key(rule: int, nodes: Iterable[PineR34Pivot]) -> tuple[object, ...]:
    material: list[object] = [rule]
    for node in nodes:
        material.extend((node.index, round(node.price, 8)))
    return tuple(material)


def scan_pine_r34(
    frame: pd.DataFrame,
    *,
    scales: tuple[int, ...] = PINE_R34_SCALES,
    atr_length: int = 14,
    min_leg_atr: float = 0.35,
    max_bars: int = 500,
    cluster_width: float = 0.12,
    structure_life: int = 180,
    tick_size: float = 0.01,
    abcd_tolerance_pct: float = 3.0,
    abcd_convergence_pct: float = 3.0,
    test_gap_bars: int = 3,
    test_session_bars: int = 12,
    test_reset_atr: float = 0.75,
    capacity: int = 180,
    unqualified_storage_limit: int = PINE_R34_UNQUALIFIED_STORAGE_LIMIT,
    candidate_table_limit: int = PINE_R34_CANDIDATE_TABLE_LIMIT,
    show_developing: bool = True,
    developing_age: int = PINE_R34_DEVELOPING_AGE,
    visible_width_atr: float = PINE_R34_VISIBLE_WIDTH_ATR,
    fresh_bars: int = PINE_R34_FRESH_BARS,
) -> PineR34Scan:
    """Sequentially reproduce the recognition portion of standalone Pine R3.4.

    This is a behavioral-parity channel, not canonical Carney identity. Patterns are born only
    when the relevant 5/10/20 pivot stream changes, persist after later pivots, and never receive
    historical PRZ tests before their birth bar.
    """

    source = _validate_frame(frame)
    if source.empty:
        return PineR34Scan(
            candidates=(),
            live_candidates=(),
            monitoring_candidates=(),
            pivots_by_scale={},
            diagnostics={},
        )

    unique_scales = tuple(sorted({int(scale) for scale in scales}))
    if any(scale < 1 for scale in unique_scales):
        raise ValueError("scales must be positive")
    highs = source["high"].tolist()
    lows = source["low"].tolist()
    opens = source["open"].tolist()
    closes = source["close"].tolist()
    atr_values = pine_atr(source, atr_length)

    streams: dict[int, list[PineR34Pivot]] = {scale: [] for scale in unique_scales}
    candidates: list[PineR34Candidate] = []
    seen: set[tuple[object, ...]] = set()
    next_id = 1
    born_counts: dict[str, int] = {}

    for bar in range(len(source)):
        current_atr = atr_values[bar]

        # Existing structures update before pivots confirmed on this bar, matching R3.4 ordering.
        if current_atr is not None:
            for candidate in candidates:
                if not candidate.live or bar <= candidate.born_bar:
                    continue
                broken = lows[bar] <= candidate.structural_limit if candidate.direction == 1 else highs[bar] >= candidate.structural_limit
                old = bar > candidate.expires_bar
                source_price = candidate.source_nodes[-1].price
                source_changed = (
                    candidate.test_count == 0
                    and candidate.coverage_mask == 0
                    and candidate.direction * (closes[bar] - source_price) > candidate.atr_at_birth * 0.25
                )
                if broken or old or source_changed:
                    candidate.live = False
                    candidate.closed_bar = bar
                    candidate.close_reason = "结构极限触发" if broken else "结构观察到期" if old else "未触区源结构被越过"
                    continue

                if not candidate.qualified:
                    continue

                previous_close = closes[bar - 1]
                gap_through = (
                    previous_close > candidate.prz_high
                    and opens[bar] < candidate.prz_low
                    and highs[bar] < candidate.prz_high
                    if candidate.direction == 1
                    else previous_close < candidate.prz_low
                    and opens[bar] > candidate.prz_high
                    and lows[bar] > candidate.prz_low
                )
                distance = _distance(closes[bar], candidate.prz_low, candidate.prz_high)
                if candidate.coverage_mask and candidate.test_start_bar is not None and candidate.test_last_bar is not None and candidate.test_atr is not None:
                    reset = (
                        gap_through
                        or bar - candidate.test_last_bar > test_gap_bars
                        or bar - candidate.test_start_bar >= test_session_bars
                        or distance > candidate.test_atr * test_reset_atr
                    )
                    if reset:
                        candidate.coverage_mask = 0
                        candidate.test_start_bar = None
                        candidate.test_last_bar = None
                        candidate.test_atr = None
                        candidate.session_resets += 1

                contact = lows[bar] <= candidate.prz_high + tick_size * 0.000001 and highs[bar] >= candidate.prz_low - tick_size * 0.000001
                if candidate.test_count == 0 and contact:
                    if candidate.test_start_bar is None:
                        candidate.test_start_bar = bar
                        candidate.test_atr = current_atr
                    candidate.test_last_bar = bar
                    candidate.coverage_mask = _coverage(
                        candidate.coverage_mask,
                        lows[bar],
                        highs[bar],
                        candidate.m1,
                        candidate.m2,
                        candidate.m3,
                        tick_size,
                    )
                    if candidate.coverage_mask == 7:
                        if candidate.first_test_bar is None:
                            candidate.first_test_bar = bar
                        candidate.test_count += 1
                        candidate.coverage_mask = 0
                        candidate.test_start_bar = None
                        candidate.test_last_bar = None
                        candidate.test_atr = None

        if current_atr is None:
            continue

        changed_scales: list[int] = []
        for scale in unique_scales:
            pivot = _strict_pivot(
                highs,
                lows,
                confirmation_bar=bar,
                strength=scale,
                scale=scale,
            )
            if _feed(streams[scale], pivot):
                changed_scales.append(scale)

        for scale in changed_scales:
            stream = streams[scale]
            for rule in range(12):
                count = _SOURCE_COUNT[rule]
                if len(stream) < count:
                    continue
                nodes = tuple(stream[-count:])
                key = _candidate_key(rule, nodes)
                if key in seen:
                    continue
                geometry = _geometry(
                    rule,
                    nodes,
                    atr=float(current_atr),
                    tick=tick_size,
                    min_leg_atr=min_leg_atr,
                    max_bars=max_bars,
                    cluster_width=cluster_width,
                    abcd_tolerance_pct=abcd_tolerance_pct,
                    abcd_convergence_pct=abcd_convergence_pct,
                )
                if not geometry.ok:
                    continue
                assert geometry.m1 is not None and geometry.m2 is not None and geometry.m3 is not None
                assert geometry.low is not None and geometry.high is not None
                assert geometry.limit is not None and geometry.reference_scale is not None

                # Mirror R3.4 storage semantics exactly here: storage pressure is based on
                # Pine's qualified flag, not HT-CN's separate Source/research policy label.
                unqualified_count = sum(not existing.qualified for existing in candidates)
                storage_pressure = (
                    len(candidates) >= capacity
                    or (
                        not geometry.qualified
                        and unqualified_count >= unqualified_storage_limit
                    )
                )
                if storage_pressure:
                    victim = next(
                        (
                            index
                            for index, existing in enumerate(candidates)
                            if (
                                (not existing.qualified)
                                if not geometry.qualified
                                else ((not existing.live) or (not existing.qualified))
                            )
                        ),
                        None,
                    )
                    if victim is not None:
                        candidates.pop(victim)
                if len(candidates) >= capacity:
                    continue
                if (
                    not geometry.qualified
                    and sum(not existing.qualified for existing in candidates)
                    >= unqualified_storage_limit
                ):
                    continue

                rounded_m1 = _tick_price(float(geometry.m1), tick_size)
                rounded_m2 = _tick_price(float(geometry.m2), tick_size)
                rounded_m3 = _tick_price(float(geometry.m3), tick_size)
                rounded_low = _tick_price(float(geometry.low), tick_size)
                rounded_high = _tick_price(float(geometry.high), tick_size)
                rounded_limit = _tick_price(float(geometry.limit), tick_size)

                candidate = PineR34Candidate(
                    candidate_id=next_id,
                    rule=rule,
                    pattern_id=_PATTERN_NAMES[rule],
                    schema=_PATTERN_SCHEMA[rule],
                    direction=geometry.direction,
                    scale=scale,
                    source_nodes=nodes,
                    source_labels=_SOURCE_LABELS[rule],
                    m1=rounded_m1,
                    m2=rounded_m2,
                    m3=rounded_m3,
                    prz_low=min(rounded_low, rounded_high),
                    prz_high=max(rounded_low, rounded_high),
                    structural_limit=rounded_limit,
                    reference_scale=float(geometry.reference_scale),
                    atr_at_birth=float(current_atr),
                    born_bar=bar,
                    expires_bar=bar + structure_life,
                    qualified=geometry.qualified,
                    precise=geometry.precise,
                    research_only=_research_only(rule, geometry.qualified, geometry.precise),
                    quality_reason=geometry.quality_reason,
                    c_ideal=geometry.c_ideal,
                    bc_ideal=geometry.bc_ideal,
                    c_error=geometry.c_error,
                    convergence_error=geometry.convergence_error,
                )
                next_id += 1
                seen.add(key)

                born_broken = lows[bar] <= candidate.structural_limit if candidate.direction == 1 else highs[bar] >= candidate.structural_limit
                source_passed = candidate.direction * (closes[bar] - nodes[-1].price) > float(current_atr) * 0.25
                if born_broken or source_passed:
                    candidate.live = False
                    candidate.closed_bar = bar
                    candidate.close_reason = "发现时源结构/边界已被越过，仅供历史研究"

                # A structure is first knowable on this confirmation bar. Current-bar contact is allowed;
                # prior bars are intentionally never replayed into the test state.
                if candidate.live and candidate.qualified:
                    contact = lows[bar] <= candidate.prz_high + tick_size * 0.000001 and highs[bar] >= candidate.prz_low - tick_size * 0.000001
                    if contact:
                        candidate.test_start_bar = bar
                        candidate.test_last_bar = bar
                        candidate.test_atr = float(current_atr)
                        candidate.coverage_mask = _coverage(
                            0,
                            lows[bar],
                            highs[bar],
                            candidate.m1,
                            candidate.m2,
                            candidate.m3,
                            tick_size,
                        )
                        if candidate.coverage_mask == 7:
                            candidate.first_test_bar = bar
                            candidate.test_count = 1
                            candidate.coverage_mask = 0
                            candidate.test_start_bar = None
                            candidate.test_last_bar = None
                            candidate.test_atr = None

                candidates.append(candidate)
                born_counts[candidate.pattern_id] = born_counts.get(candidate.pattern_id, 0) + 1

    latest_bar = len(source) - 1
    latest_close = closes[-1]
    latest_atr = atr_values[-1]
    live_items = [candidate for candidate in candidates if candidate.live]
    if latest_atr is not None and latest_atr > 0:
        for candidate in live_items:
            distance = _distance(
                latest_close,
                candidate.prz_low,
                candidate.prz_high,
            )
            candidate.current_distance_atr = distance / latest_atr
            candidate.current_distance_pct = (
                distance / latest_close * 100.0
                if latest_close > 0
                else None
            )
            candidate.source_age = max(
                0,
                latest_bar - candidate.source_nodes[-1].index,
            )
            candidate.observable = _observable(
                latest_close,
                candidate.prz_low,
                candidate.prz_high,
                latest_atr,
                visible_width_atr=visible_width_atr,
            )
            candidate.recently_tested = (
                candidate.first_test_bar is not None
                and latest_bar - candidate.first_test_bar <= fresh_bars
            )
            candidate.monitoring_rank = _candidate_rank(
                near_enough=candidate.observable,
                active_event=candidate.recently_tested,
                rule=candidate.rule,
                source_age=candidate.source_age,
                distance_atr=candidate.current_distance_atr,
            ) - (0.0 if candidate.qualified else 1000000.0)

    live = tuple(
        sorted(
            live_items,
            key=lambda item: (
                -(
                    item.monitoring_rank
                    if item.monitoring_rank is not None
                    else -1e20
                ),
                item.research_only,
                -(item.born_bar),
                -item.scale,
                item.pattern_id,
            ),
        )
    )
    monitoring = tuple(
        item
        for item in live
        if _candidate_visible(
            live=item.live,
            near_enough=item.observable,
            developing=show_developing,
            age=item.source_age if item.source_age is not None else 10**9,
            max_age=developing_age,
            research=False,
        )
    )[:candidate_table_limit]
    return PineR34Scan(
        candidates=tuple(candidates),
        live_candidates=live,
        monitoring_candidates=monitoring,
        pivots_by_scale={scale: tuple(stream) for scale, stream in streams.items()},
        diagnostics={
            "pine_source_sha256": PINE_R34_SOURCE_SHA256,
            "bars": len(source),
            "candidate_count": len(candidates),
            "live_candidate_count": len(live),
            "monitoring_candidate_count": len(monitoring),
            "hidden_remote_count": sum(
                item.live and not item.observable
                for item in candidates
            ),
            "pine_unqualified_live_count": sum(
                item.live and not item.qualified
                for item in candidates
            ),
            "htcn_research_live_count": sum(
                item.live and item.research_only
                for item in candidates
            ),
            "born_counts": born_counts,
            "scales": list(unique_scales),
            "atr_length": atr_length,
            "min_leg_atr": min_leg_atr,
            "cluster_width": cluster_width,
            "structure_life": structure_life,
            "candidate_table_limit": candidate_table_limit,
            "developing_age": developing_age,
            "visible_width_atr": visible_width_atr,
        },
    )
