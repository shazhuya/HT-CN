from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from itertools import product
from typing import Protocol


class PRZComponentLike(Protocol):
    name: str
    price_low: float
    price_high: float
    ratio_low: float
    ratio_high: float

    @property
    def midpoint(self) -> float: ...


@dataclass(frozen=True, slots=True)
class SourcePRZProfile:
    """Pattern-specific source membership for an executable Raw PRZ.

    This registry does not decide harmonic identity.  It only specifies which already-built,
    source-valid measurements may participate in the Raw PRZ and how competing discrete
    measurements are reduced to one executable convergence set.
    """

    pattern_id: str
    status: str
    defining_component: str
    bc_ratios: tuple[float, ...]
    abcd_ratios: tuple[float, ...]
    selection_method: str
    source_refs: tuple[str, ...]
    note: str

    def __post_init__(self) -> None:
        if self.status not in {"frozen", "source_conflict", "unresolved"}:
            raise ValueError(f"unsupported source PRZ status: {self.status}")
        if self.selection_method not in {"compact_three_measure", "xa_bc_primary", "none"}:
            raise ValueError(f"unsupported source PRZ selection method: {self.selection_method}")
        if self.status == "frozen" and self.selection_method == "none":
            raise ValueError("frozen source PRZ profile requires an executable selection method")


@dataclass(frozen=True, slots=True)
class SourcePRZSelection:
    pattern_id: str
    status: str
    price_low: float | None
    price_high: float | None
    component_names: tuple[str, ...]
    defining_component: str | None
    selection_method: str | None
    source_refs: tuple[str, ...]
    note: str
    reason: str | None = None

    @property
    def available(self) -> bool:
        return self.price_low is not None and self.price_high is not None and self.status == "frozen"


# Page labels below refer to the printed page numbers in the selected Carney volumes, not the
# PDF viewer's physical page index.  The profile freezes source membership, not a claim that
# every market example must use the same exact complementary ratio.
SOURCE_PRZ_PROFILES: dict[str, SourcePRZProfile] = {
    "gartley": SourcePRZProfile(
        pattern_id="gartley",
        status="frozen",
        defining_component="XA completion",
        bc_ratios=(1.13, 1.27, 1.414, 1.618),
        abcd_ratios=(1.0, 1.27),
        selection_method="compact_three_measure",
        source_refs=("Volume One pp.104-105", "Volume Three p.92"),
        note=(
            "0.786 XA and a distinct AB=CD define the Gartley PRZ; a BC projection no greater "
            "than 1.618 complements the same area."
        ),
    ),
    "bat": SourcePRZProfile(
        pattern_id="bat",
        status="frozen",
        defining_component="XA completion",
        bc_ratios=(2.0, 1.618, 2.24, 2.618),
        abcd_ratios=(1.27, 1.0, 1.618),
        selection_method="compact_three_measure",
        source_refs=("Volume One pp.79-99", "Volume Three p.98"),
        note=(
            "0.886 XA is the defining Bat completion.  Source examples repeatedly form the "
            "Raw PRZ from that level plus a convergent BC projection and minimum/alternate AB=CD."
        ),
    ),
    "alternate_bat": SourcePRZProfile(
        pattern_id="alternate_bat",
        status="source_conflict",
        defining_component="XA completion",
        bc_ratios=(2.0, 2.24, 2.618, 3.14, 3.618),
        abcd_ratios=(),
        selection_method="none",
        source_refs=("Volume Two Alternate Bat chapter", "Volume Three p.101"),
        note=(
            "Volume Two excludes AB=CD from the setup while Volume Three explicitly lists "
            "1.618 AB=CD.  Raw PRZ remains fail-closed until figure-level reconciliation."
        ),
    ),
    "butterfly": SourcePRZProfile(
        pattern_id="butterfly",
        status="frozen",
        defining_component="XA completion",
        bc_ratios=(1.618, 2.0, 2.24),
        abcd_ratios=(1.27, 1.0),
        selection_method="compact_three_measure",
        source_refs=("Volume One pp.151-166", "Volume Three p.113"),
        note=(
            "1.27 XA is the defining Butterfly limit; equivalent/1.27 AB=CD and a compact "
            "1.618-2.24 BC projection complete the source PRZ."
        ),
    ),
    "crab": SourcePRZProfile(
        pattern_id="crab",
        status="frozen",
        defining_component="XA completion",
        bc_ratios=(3.14, 2.618, 3.618),
        abcd_ratios=(1.618, 1.27, 1.0),
        selection_method="xa_bc_primary",
        source_refs=("Volume One pp.125-134", "Volume Three p.104"),
        note=(
            "1.618 XA and the extreme BC projection define the principal Crab completion range. "
            "AB=CD remains part of the three-measure PRZ but is explicitly lower priority."
        ),
    ),
    "deep_crab": SourcePRZProfile(
        pattern_id="deep_crab",
        status="frozen",
        defining_component="XA completion",
        bc_ratios=(3.14, 2.618, 2.24, 2.0, 3.618),
        abcd_ratios=(1.27, 1.0, 1.618),
        selection_method="compact_three_measure",
        source_refs=("Volume One pp.139-143", "Volume Three p.107"),
        note=(
            "Deep Crab keeps 1.618 XA as the defining limit, with a 2.0-3.618 BC family and "
            "a comparatively important equivalent/alternate AB=CD measurement."
        ),
    ),
}


def _ratio_matches(value: float, target: float) -> bool:
    return abs(float(value) - float(target)) <= 1e-9 * max(1.0, abs(float(value)), abs(float(target)))


def _matching_components(
    components: Sequence[PRZComponentLike],
    *,
    prefix: str,
    allowed_ratios: tuple[float, ...],
) -> list[PRZComponentLike]:
    matched: list[PRZComponentLike] = []
    for component in components:
        if not component.name.startswith(prefix):
            continue
        if any(_ratio_matches(component.ratio_low, ratio) and _ratio_matches(component.ratio_high, ratio) for ratio in allowed_ratios):
            matched.append(component)
    return matched


def _preference_rank(component: PRZComponentLike, ratios: tuple[float, ...]) -> int:
    for index, ratio in enumerate(ratios):
        if _ratio_matches(component.ratio_low, ratio) and _ratio_matches(component.ratio_high, ratio):
            return index
    return len(ratios)


def _zone_bounds(components: Sequence[PRZComponentLike]) -> tuple[float, float]:
    return (
        min(float(component.price_low) for component in components),
        max(float(component.price_high) for component in components),
    )


def _distance_to_interval(value: float, low: float, high: float) -> float:
    if low <= value <= high:
        return 0.0
    return min(abs(value - low), abs(value - high))


def _select_compact_three_measure(
    profile: SourcePRZProfile,
    defining: PRZComponentLike,
    bc_components: Sequence[PRZComponentLike],
    abcd_components: Sequence[PRZComponentLike],
) -> tuple[PRZComponentLike, PRZComponentLike]:
    anchor = float(defining.midpoint)

    def score(pair: tuple[PRZComponentLike, PRZComponentLike]) -> tuple[float, float, int, int, str, str]:
        bc, abcd = pair
        low, high = _zone_bounds((defining, bc, abcd))
        anchor_distance = abs(float(bc.midpoint) - anchor) + abs(float(abcd.midpoint) - anchor)
        return (
            high - low,
            anchor_distance,
            _preference_rank(abcd, profile.abcd_ratios),
            _preference_rank(bc, profile.bc_ratios),
            bc.name,
            abcd.name,
        )

    return min(product(bc_components, abcd_components), key=score)


def _select_xa_bc_primary(
    profile: SourcePRZProfile,
    defining: PRZComponentLike,
    bc_components: Sequence[PRZComponentLike],
    abcd_components: Sequence[PRZComponentLike],
) -> tuple[PRZComponentLike, PRZComponentLike]:
    """Crab-specific priority: XA + BC first, then choose AB=CD that best complements them."""

    anchor = float(defining.midpoint)
    bc = min(
        bc_components,
        key=lambda item: (
            abs(float(item.midpoint) - anchor),
            _preference_rank(item, profile.bc_ratios),
            item.name,
        ),
    )
    primary_low, primary_high = _zone_bounds((defining, bc))
    abcd = min(
        abcd_components,
        key=lambda item: (
            _distance_to_interval(float(item.midpoint), primary_low, primary_high),
            _preference_rank(item, profile.abcd_ratios),
            item.name,
        ),
    )
    return bc, abcd


def select_source_prz(
    pattern_id: str,
    components: Sequence[PRZComponentLike],
) -> SourcePRZSelection:
    """Select one auditable source Raw PRZ from already-projected discrete measurements.

    The function intentionally fails closed for missing profiles, unresolved profiles, source
    conflicts, or incomplete component sets.  It never falls back to the HT-CN ideal core or the
    all-component audit envelope.
    """

    profile = SOURCE_PRZ_PROFILES.get(pattern_id)
    if profile is None:
        return SourcePRZSelection(
            pattern_id=pattern_id,
            status="unresolved",
            price_low=None,
            price_high=None,
            component_names=(),
            defining_component=None,
            selection_method=None,
            source_refs=(),
            note="No source PRZ profile is frozen for this pattern.",
            reason="profile_missing",
        )
    if profile.status != "frozen":
        return SourcePRZSelection(
            pattern_id=pattern_id,
            status=profile.status,
            price_low=None,
            price_high=None,
            component_names=(),
            defining_component=profile.defining_component,
            selection_method=profile.selection_method,
            source_refs=profile.source_refs,
            note=profile.note,
            reason="source_conflict" if profile.status == "source_conflict" else "profile_unresolved",
        )

    defining = next((component for component in components if component.name == profile.defining_component), None)
    if defining is None:
        return SourcePRZSelection(
            pattern_id=pattern_id,
            status="unresolved",
            price_low=None,
            price_high=None,
            component_names=(),
            defining_component=profile.defining_component,
            selection_method=profile.selection_method,
            source_refs=profile.source_refs,
            note=profile.note,
            reason="defining_component_missing",
        )

    bc_components = _matching_components(
        components,
        prefix="BC projection",
        allowed_ratios=profile.bc_ratios,
    )
    abcd_components = _matching_components(
        components,
        prefix="AB=CD",
        allowed_ratios=profile.abcd_ratios,
    )
    if not bc_components or not abcd_components:
        missing = []
        if not bc_components:
            missing.append("bc")
        if not abcd_components:
            missing.append("abcd")
        return SourcePRZSelection(
            pattern_id=pattern_id,
            status="unresolved",
            price_low=None,
            price_high=None,
            component_names=(),
            defining_component=profile.defining_component,
            selection_method=profile.selection_method,
            source_refs=profile.source_refs,
            note=profile.note,
            reason=f"required_components_missing:{'+'.join(missing)}",
        )

    if profile.selection_method == "compact_three_measure":
        bc, abcd = _select_compact_three_measure(profile, defining, bc_components, abcd_components)
    elif profile.selection_method == "xa_bc_primary":
        bc, abcd = _select_xa_bc_primary(profile, defining, bc_components, abcd_components)
    else:  # pragma: no cover - profile validation prevents this path
        raise ValueError(f"non-executable source PRZ method: {profile.selection_method}")

    selected = (defining, bc, abcd)
    low, high = _zone_bounds(selected)
    return SourcePRZSelection(
        pattern_id=pattern_id,
        status="frozen",
        price_low=low,
        price_high=high,
        component_names=tuple(component.name for component in selected),
        defining_component=profile.defining_component,
        selection_method=profile.selection_method,
        source_refs=profile.source_refs,
        note=profile.note,
        reason=None,
    )
