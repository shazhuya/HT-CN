from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from typing import Iterable

import pandas as pd

from .indicators import wilder_rsi


RSI_BAMM_SOURCE_DEFINITION = "rsi-bamm-source-v1"
RSI_BAMM_PERIOD = 14
RSI_OVERSOLD = 30.0
RSI_OVERBOUGHT = 70.0
RSI_MIDPOINT = 50.0


class RSIBammDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class RSIBammStructureKind(str, Enum):
    IMPULSIVE = "impulsive"
    COMPLEX = "complex"


class RSIBammRelation(str, Enum):
    CONFIRMATION = "confirmation"
    DIVERGENCE = "divergence"


class RSIBammProfile(str, Enum):
    SIMPLE_CONFIRMATION = "simple_confirmation"
    COMPLEX_CONFIRMATION = "complex_confirmation"
    SIMPLE_DIVERGENCE = "simple_divergence"
    COMPLEX_DIVERGENCE = "complex_divergence"


@dataclass(frozen=True, slots=True)
class RSIBammStructure:
    direction: RSIBammDirection
    kind: RSIBammStructureKind
    enter_bar: int
    exit_bar: int
    rsi_extreme_bar: int
    rsi_extreme_value: float
    price_extreme_bar: int
    price_extreme_value: float
    exit_rsi: float

    @property
    def bars_in_extreme(self) -> int:
        return self.exit_bar - self.enter_bar


@dataclass(frozen=True, slots=True)
class RSIBammSequence:
    direction: RSIBammDirection
    profile: RSIBammProfile
    relation: RSIBammRelation
    first_structure: RSIBammStructure
    midpoint_bar: int
    midpoint_rsi: float
    second_structure: RSIBammStructure
    trigger_bar: int
    trigger_reference_price: float
    trigger_to_prior_price_extreme_bars: int
    confirmation_extension_ratio: float
    confirmation_extension_basis: str
    source_definition: str = RSI_BAMM_SOURCE_DEFINITION
    indicator_sequence_complete: bool = True
    price_projection_resolved: bool = False
    harmonic_confluence_required: bool = True
    mutates_harmonic_identity: bool = False

    @property
    def completion_bar(self) -> int:
        return self.second_structure.exit_bar


@dataclass(frozen=True, slots=True)
class RSIBammConfirmation:
    sequence: RSIBammSequence
    price_confirmation_tested: bool
    harmonic_pattern_completed: bool
    status: str

    @property
    def source_confirmed(self) -> bool:
        return self.status == "source_confirmed"


def _finite_series(values: Iterable[float] | pd.Series, *, name: str) -> pd.Series:
    series = pd.Series(values, dtype="float64").reset_index(drop=True)
    if series.empty:
        return series
    if series.isna().any() or not all(math.isfinite(float(value)) for value in series):
        raise ValueError(f"{name} contains non-finite values")
    return series


def _is_extreme(value: float, direction: RSIBammDirection) -> bool:
    if direction is RSIBammDirection.BULLISH:
        return value < RSI_OVERSOLD
    return value > RSI_OVERBOUGHT


def _midpoint_reached(value: float, direction: RSIBammDirection) -> bool:
    if direction is RSIBammDirection.BULLISH:
        return value >= RSI_MIDPOINT
    return value <= RSI_MIDPOINT


def _complex_shape(values: list[float], direction: RSIBammDirection) -> bool:
    """Conservative W/M operationalization inside the 30/70 extreme zone.

    Carney defines a complex bullish structure as a W-type formation entirely below 30
    and a complex bearish structure as an M-type formation entirely above 70. The books
    do not publish a bar-by-bar pivot algorithm, so HT-CN records this as an engineering
    operationalization: a complex structure needs an internal recovery/pullback followed
    by a second turn before the extreme-zone exit. This classifier never changes harmonic
    pattern identity or Source Raw PRZ.
    """
    if len(values) < 3:
        return False

    if direction is RSIBammDirection.BULLISH:
        saw_recovery = False
        for left, right in zip(values, values[1:]):
            if right > left:
                saw_recovery = True
            elif saw_recovery and right < left:
                return True
        return False

    saw_pullback = False
    for left, right in zip(values, values[1:]):
        if right < left:
            saw_pullback = True
        elif saw_pullback and right > left:
            return True
    return False


def _finish_structure(
    *,
    direction: RSIBammDirection,
    enter_bar: int,
    exit_bar: int,
    rsi: pd.Series,
    lows: pd.Series,
    highs: pd.Series,
) -> RSIBammStructure:
    extreme_values = [float(value) for value in rsi.iloc[enter_bar:exit_bar]]
    if not extreme_values:
        raise ValueError("RSI BAMM extreme structure has no extreme observations")

    kind = (
        RSIBammStructureKind.COMPLEX
        if _complex_shape(extreme_values, direction)
        else RSIBammStructureKind.IMPULSIVE
    )

    if direction is RSIBammDirection.BULLISH:
        rsi_slice = rsi.iloc[enter_bar:exit_bar]
        rsi_extreme_bar = int(rsi_slice.idxmin())
        rsi_extreme_value = float(rsi.loc[rsi_extreme_bar])
        price_slice = lows.iloc[enter_bar : exit_bar + 1]
        price_extreme_bar = int(price_slice.idxmin())
        price_extreme_value = float(lows.loc[price_extreme_bar])
    else:
        rsi_slice = rsi.iloc[enter_bar:exit_bar]
        rsi_extreme_bar = int(rsi_slice.idxmax())
        rsi_extreme_value = float(rsi.loc[rsi_extreme_bar])
        price_slice = highs.iloc[enter_bar : exit_bar + 1]
        price_extreme_bar = int(price_slice.idxmax())
        price_extreme_value = float(highs.loc[price_extreme_bar])

    return RSIBammStructure(
        direction=direction,
        kind=kind,
        enter_bar=int(enter_bar),
        exit_bar=int(exit_bar),
        rsi_extreme_bar=rsi_extreme_bar,
        rsi_extreme_value=rsi_extreme_value,
        price_extreme_bar=price_extreme_bar,
        price_extreme_value=price_extreme_value,
        exit_rsi=float(rsi.iloc[exit_bar]),
    )


def _relation(
    first: RSIBammStructure,
    second: RSIBammStructure,
) -> RSIBammRelation | None:
    if first.direction is not second.direction:
        return None

    if first.direction is RSIBammDirection.BULLISH:
        if second.rsi_extreme_value <= first.rsi_extreme_value:
            return None
        if second.price_extreme_value > first.price_extreme_value:
            return RSIBammRelation.CONFIRMATION
        if second.price_extreme_value < first.price_extreme_value:
            return RSIBammRelation.DIVERGENCE
        return None

    if second.rsi_extreme_value >= first.rsi_extreme_value:
        return None
    if second.price_extreme_value < first.price_extreme_value:
        return RSIBammRelation.CONFIRMATION
    if second.price_extreme_value > first.price_extreme_value:
        return RSIBammRelation.DIVERGENCE
    return None


def _profile(
    first: RSIBammStructure,
    relation: RSIBammRelation,
) -> RSIBammProfile:
    if first.kind is RSIBammStructureKind.IMPULSIVE:
        return (
            RSIBammProfile.SIMPLE_CONFIRMATION
            if relation is RSIBammRelation.CONFIRMATION
            else RSIBammProfile.SIMPLE_DIVERGENCE
        )
    return (
        RSIBammProfile.COMPLEX_CONFIRMATION
        if relation is RSIBammRelation.CONFIRMATION
        else RSIBammProfile.COMPLEX_DIVERGENCE
    )


def _extension_contract(
    first: RSIBammStructure,
    lows: pd.Series,
    highs: pd.Series,
) -> tuple[int, float, int, float, str]:
    """Freeze the source-resolved 1.13-vs-1.618 ratio-selection rule only.

    Volume Two ties 1.618 to a Trigger Bar at the prior price extreme and 1.13 to a
    Trigger Bar that is not that extreme (commonly a few bars later). The exact X-A
    projection coordinate construction is deliberately not invented in this phase; the
    selected ratio is returned without a target price until figure-level anchors are frozen.
    """
    trigger_bar = int(first.exit_bar)
    trigger_reference = (
        float(lows.iloc[trigger_bar])
        if first.direction is RSIBammDirection.BULLISH
        else float(highs.iloc[trigger_bar])
    )
    offset = abs(trigger_bar - int(first.price_extreme_bar))
    if offset == 0:
        return (
            trigger_bar,
            trigger_reference,
            offset,
            1.618,
            "trigger_bar_is_prior_price_extreme",
        )
    return (
        trigger_bar,
        trigger_reference,
        offset,
        1.13,
        "trigger_bar_is_not_prior_price_extreme",
    )


def _build_sequence(
    *,
    first: RSIBammStructure,
    midpoint_bar: int,
    midpoint_rsi: float,
    second: RSIBammStructure,
    lows: pd.Series,
    highs: pd.Series,
) -> RSIBammSequence | None:
    # Volume Three: Simple uses two impulsive tests; Complex starts complex and
    # finishes with an impulsive retest. Therefore the second test is always impulsive.
    if second.kind is not RSIBammStructureKind.IMPULSIVE:
        return None

    relation = _relation(first, second)
    if relation is None:
        return None

    trigger_bar, trigger_reference, offset, ratio, basis = _extension_contract(
        first,
        lows,
        highs,
    )
    return RSIBammSequence(
        direction=first.direction,
        profile=_profile(first, relation),
        relation=relation,
        first_structure=first,
        midpoint_bar=int(midpoint_bar),
        midpoint_rsi=float(midpoint_rsi),
        second_structure=second,
        trigger_bar=trigger_bar,
        trigger_reference_price=trigger_reference,
        trigger_to_prior_price_extreme_bars=offset,
        confirmation_extension_ratio=ratio,
        confirmation_extension_basis=basis,
    )


def scan_rsi_bamm_values(
    rsi_values: Iterable[float] | pd.Series,
    *,
    lows: Iterable[float] | pd.Series,
    highs: Iterable[float] | pd.Series,
    direction: RSIBammDirection,
) -> list[RSIBammSequence]:
    """Scan completed RSI BAMM indicator sequences without look-ahead.

    A sequence is emitted only when the second extreme structure exits its 30/70 zone.
    At that bar all structural evidence is observable: first extreme structure, mandatory
    50-midpoint reaction, secondary impulsive retest and price/RSI confirmation or
    divergence relationship.

    The result is an indicator sequence, not a trade-ready Harmonic Trading setup. Volume
    Two coordinates the Confirmation Point with a harmonic pattern and a 1.13/1.618 price
    projection. Until that price projection is fully source-frozen, the result remains
    ``price_projection_resolved=False`` and fails closed at the final confirmation layer.
    """
    rsi = _finite_series(rsi_values, name="rsi")
    low_series = _finite_series(lows, name="lows")
    high_series = _finite_series(highs, name="highs")
    if not (len(rsi) == len(low_series) == len(high_series)):
        raise ValueError("rsi/lows/highs must have equal lengths")
    if any(float(high) < float(low) for high, low in zip(high_series, low_series)):
        raise ValueError("highs must be >= lows")

    sequences: list[RSIBammSequence] = []
    first: RSIBammStructure | None = None
    midpoint_bar: int | None = None
    midpoint_rsi: float | None = None
    active_enter: int | None = None

    for bar in range(len(rsi)):
        value = float(rsi.iloc[bar])
        extreme = _is_extreme(value, direction)

        if active_enter is None and extreme:
            active_enter = bar
            continue
        if active_enter is not None and extreme:
            continue

        if active_enter is not None:
            structure = _finish_structure(
                direction=direction,
                enter_bar=active_enter,
                exit_bar=bar,
                rsi=rsi,
                lows=low_series,
                highs=high_series,
            )
            active_enter = None

            if first is None:
                first = structure
                midpoint_bar = bar if _midpoint_reached(value, direction) else None
                midpoint_rsi = value if midpoint_bar is not None else None
                continue

            if midpoint_bar is None:
                # An extreme retest before the mandatory 50 reaction invalidates the older
                # pairing. Promote the new structure instead of rescuing it with future data.
                first = structure
                midpoint_bar = bar if _midpoint_reached(value, direction) else None
                midpoint_rsi = value if midpoint_bar is not None else None
                continue

            sequence = _build_sequence(
                first=first,
                midpoint_bar=midpoint_bar,
                midpoint_rsi=float(midpoint_rsi),
                second=structure,
                lows=low_series,
                highs=high_series,
            )
            if sequence is not None:
                sequences.append(sequence)

            # The completed secondary extreme may seed a later sequence, but only after a
            # fresh midpoint reaction. This keeps chained detections chronological.
            first = structure
            midpoint_bar = bar if _midpoint_reached(value, direction) else None
            midpoint_rsi = value if midpoint_bar is not None else None
            continue

        if first is not None and midpoint_bar is None and _midpoint_reached(value, direction):
            midpoint_bar = bar
            midpoint_rsi = value

    return sequences


def scan_rsi_bamm_frame(
    frame: pd.DataFrame,
    *,
    direction: RSIBammDirection,
    period: int = RSI_BAMM_PERIOD,
) -> list[RSIBammSequence]:
    """Compute Wilder RSI and run the dedicated BAMM state machine."""
    required = {"close", "low", "high"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"RSI BAMM frame missing columns: {sorted(missing)}")
    if period < 2:
        raise ValueError("period must be >= 2")

    source = frame.reset_index(drop=True)
    rsi = wilder_rsi(source["close"], period=period)
    valid = rsi.notna()
    if not valid.any():
        return []
    start = int(valid.idxmax())

    rows = scan_rsi_bamm_values(
        rsi.iloc[start:].reset_index(drop=True),
        lows=pd.to_numeric(source["low"].iloc[start:], errors="raise").reset_index(drop=True),
        highs=pd.to_numeric(source["high"].iloc[start:], errors="raise").reset_index(drop=True),
        direction=direction,
    )

    def shift_structure(item: RSIBammStructure) -> RSIBammStructure:
        return RSIBammStructure(
            direction=item.direction,
            kind=item.kind,
            enter_bar=item.enter_bar + start,
            exit_bar=item.exit_bar + start,
            rsi_extreme_bar=item.rsi_extreme_bar + start,
            rsi_extreme_value=item.rsi_extreme_value,
            price_extreme_bar=item.price_extreme_bar + start,
            price_extreme_value=item.price_extreme_value,
            exit_rsi=item.exit_rsi,
        )

    shifted: list[RSIBammSequence] = []
    for row in rows:
        shifted.append(
            RSIBammSequence(
                direction=row.direction,
                profile=row.profile,
                relation=row.relation,
                first_structure=shift_structure(row.first_structure),
                midpoint_bar=row.midpoint_bar + start,
                midpoint_rsi=row.midpoint_rsi,
                second_structure=shift_structure(row.second_structure),
                trigger_bar=row.trigger_bar + start,
                trigger_reference_price=row.trigger_reference_price,
                trigger_to_prior_price_extreme_bars=row.trigger_to_prior_price_extreme_bars,
                confirmation_extension_ratio=row.confirmation_extension_ratio,
                confirmation_extension_basis=row.confirmation_extension_basis,
                source_definition=row.source_definition,
                indicator_sequence_complete=row.indicator_sequence_complete,
                price_projection_resolved=row.price_projection_resolved,
                harmonic_confluence_required=row.harmonic_confluence_required,
                mutates_harmonic_identity=row.mutates_harmonic_identity,
            )
        )
    return shifted


def confirm_rsi_bamm(
    sequence: RSIBammSequence,
    *,
    price_confirmation_tested: bool,
    harmonic_pattern_completed: bool,
) -> RSIBammConfirmation:
    """Combine BAMM indicator evidence with the still-separate price/pattern layer.

    M2.31 Phase 1 intentionally fails closed because the exact X-A price projection
    coordinates have not yet been frozen from the book figures. Supplying booleans cannot
    bypass that source gap.
    """
    if not sequence.price_projection_resolved:
        status = "source_confirmation_blocked_projection_unresolved"
    elif price_confirmation_tested and harmonic_pattern_completed:
        status = "source_confirmed"
    elif price_confirmation_tested:
        status = "price_confirmation_without_harmonic_pattern"
    elif harmonic_pattern_completed:
        status = "harmonic_pattern_without_price_confirmation"
    else:
        status = "indicator_sequence_only"

    return RSIBammConfirmation(
        sequence=sequence,
        price_confirmation_tested=bool(price_confirmation_tested),
        harmonic_pattern_completed=bool(harmonic_pattern_completed),
        status=status,
    )
