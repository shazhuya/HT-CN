from __future__ import annotations

from dataclasses import dataclass

PINE_R35_SOURCE_SHA256 = "8bc49dc1ac2d0e6b829968aea0e72450c413bb0a0d8c1b1f6eabef57061ad68f"
PINE_R35_NEIGHBORHOOD_ATR = 0.25
PINE_R35_NEIGHBORHOOD_PCT = 0.5
PINE_R35_NEIGHBORHOOD_LIFE = 60


@dataclass(slots=True)
class PineR35Neighborhood:
    """R3.5 neighborhood state, intentionally separate from strict PRZ tests."""

    pad: float
    state: int = 0
    born: int | None = None
    first_extreme: float | None = None
    first_bar: int | None = None
    response_bar: int | None = None
    response_price: float | None = None
    reaction_peak: float | None = None
    away: bool = False
    away_bar: int | None = None
    second_bar: int | None = None
    second_extreme: float | None = None
    second_response_bar: int | None = None
    second_response_price: float | None = None
    reason: str = "未进入邻域"

    def as_payload(self, *, prz_low: float, prz_high: float) -> dict[str, object]:
        return {
            "source": "pine_r35",
            "pine_source_sha256": PINE_R35_SOURCE_SHA256,
            "state": self.state,
            "pad": self.pad,
            "zone_low": prz_low - self.pad,
            "zone_high": prz_high + self.pad,
            "born_bar": self.born,
            "first_extreme": self.first_extreme,
            "first_bar": self.first_bar,
            "response_bar": self.response_bar,
            "response_price": self.response_price,
            "reaction_peak": self.reaction_peak,
            "away": self.away,
            "away_bar": self.away_bar,
            "second_bar": self.second_bar,
            "second_extreme": self.second_extreme,
            "second_response_bar": self.second_response_bar,
            "second_response_price": self.second_response_price,
            "reason": self.reason,
            "strict_takeover": self.state == 6,
            "strict_prz_expanded": False,
            "creates_tbar": False,
            "creates_type_i": False,
            "creates_type_ii": False,
            "creates_trade_plan": False,
        }


def neighborhood_pad(
    atr_at_birth: float,
    theoretical_level: float,
    *,
    atr_fraction: float = PINE_R35_NEIGHBORHOOD_ATR,
    percent: float = PINE_R35_NEIGHBORHOOD_PCT,
) -> float:
    if atr_at_birth <= 0 or theoretical_level <= 0:
        return 0.0
    return max(
        0.0,
        min(
            atr_at_birth * atr_fraction,
            abs(theoretical_level) * percent / 100.0,
        ),
    )


def step_neighborhood(
    state: PineR35Neighborhood,
    *,
    direction: int,
    prz_low: float,
    prz_high: float,
    atr_at_birth: float,
    low: float,
    high: float,
    open_price: float,
    close: float,
    previous_high: float,
    previous_low: float,
    bar: int,
    strict_tested: bool,
    live: bool,
    window: int = PINE_R35_NEIGHBORHOOD_LIFE,
    away_fraction: float = 0.75,
    tick_size: float = 0.01,
) -> bool:
    """Faithful port of the R3.5 neighborhood transition function."""

    if direction not in (-1, 1):
        raise ValueError("direction must be -1 or 1")
    prior = state.state
    zone_low = prz_low - state.pad
    zone_high = prz_high + state.pad
    contact = low <= zone_high and high >= zone_low
    extreme = low if direction == 1 else high
    opposite = direction * (close - open_price) > 0
    response = opposite and (
        (close > zone_high and close > previous_high)
        if direction == 1
        else (close < zone_low and close < previous_low)
    )
    away_now = (
        close > zone_high + atr_at_birth * away_fraction
        if direction == 1
        else close < zone_low - atr_at_birth * away_fraction
    )

    if strict_tested and 0 < state.state < 5:
        state.state = 6
        state.reason = "后续严格测试已完成；此前邻域反应保留，不改写成T-Bar"
    elif not live and 0 < state.state < 5:
        state.state = 5
        state.reason = "母结构关闭；邻域观察结束"
    elif live and not strict_tested and state.state < 5:
        if state.state > 0 and state.born is not None and bar - state.born >= window:
            state.state = 5
            state.reason = "邻域观察超时"
        elif state.state == 0 and contact:
            state.state = 1
            state.born = bar
            state.first_extreme = extreme
            state.first_bar = bar
            state.reason = "已进入工程邻域；严格测量尚未完整测试"
        elif state.state == 1:
            if (
                contact
                and state.first_extreme is not None
                and direction * (extreme - state.first_extreme) < 0
            ):
                state.first_extreme = extreme
                state.first_bar = bar
            if response and state.born is not None and bar > state.born:
                state.state = 2
                state.response_bar = bar
                state.response_price = close
                state.reaction_peak = close
                state.away = away_now
                state.away_bar = bar if away_now else None
                state.reason = "邻域反应已发生；非严格Type-I，不追认成交"
        elif state.state == 2:
            if state.reaction_peak is None:
                state.reaction_peak = close
            else:
                state.reaction_peak = (
                    max(state.reaction_peak, high)
                    if direction == 1
                    else min(state.reaction_peak, low)
                )
            if (
                not contact
                and state.reaction_peak is not None
                and direction * (state.reaction_peak - close) >= atr_at_birth * 0.5
            ):
                state.reason = "首次邻域反应后回吐；尚未回到本版邻域"
            if not state.away and away_now:
                state.away = True
                state.away_bar = bar
            if (
                state.away
                and state.away_bar is not None
                and bar > state.away_bar
                and contact
            ):
                state.state = 3
                state.second_bar = bar
                state.second_extreme = extreme
                state.reason = "反应后再回邻域；待新低点/高点与反应，非严格Type-II"
        elif state.state == 3:
            if (
                contact
                and state.second_extreme is not None
                and direction * (extreme - state.second_extreme) < 0
            ):
                state.second_extreme = extreme
                state.second_bar = bar
            if response and state.second_bar is not None and bar > state.second_bar:
                state.state = 4
                state.second_response_bar = bar
                state.second_response_price = close
                state.reason = "邻域二次反应；严格Type-II尚未成立"
        elif state.state == 4:
            if (
                state.second_extreme is not None
                and direction * (extreme - state.second_extreme) < -tick_size * 0.5
            ) or contact:
                state.state = 5
                state.reason = "二次反应后再次回区/破极值；结束，不生成Type-III"

    return state.state != prior
