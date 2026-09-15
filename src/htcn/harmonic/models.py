from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class PatternDirection(str, Enum):
    BULLISH = "bullish"
    BEARISH = "bearish"


class PatternState(str, Enum):
    FORMING = "forming"
    COMPLETED = "completed"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class HarmonicPoint:
    """Immutable semantic point used by the harmonic engine.

    `index` is the bar position in the source series. `label` is semantic (X/A/B/C/D,
    0/X/A/B/C, etc.) and must never depend on screen coordinates.
    """

    label: str
    index: int
    price: float

    def __post_init__(self) -> None:
        if not self.label:
            raise ValueError("label must not be empty")
        if self.index < 0:
            raise ValueError("index must be >= 0")
        if self.price <= 0:
            raise ValueError("price must be positive")


@dataclass(frozen=True, slots=True)
class RatioMeasurement:
    """Auditable ratio result between two price legs."""

    name: str
    numerator: float
    denominator: float
    value: float

    def __post_init__(self) -> None:
        if self.denominator <= 0:
            raise ValueError("denominator must be positive")
        if self.numerator < 0:
            raise ValueError("numerator must be non-negative")
        if self.value < 0:
            raise ValueError("ratio value must be non-negative")
