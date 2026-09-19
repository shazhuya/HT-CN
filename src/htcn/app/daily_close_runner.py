from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class DailyClosePreflight:
    product_lane_ready: bool
    research_lane_ready: bool
    branch: str | None
    head: str | None
    worktree_clean: bool
    repository_available: bool
    catalog_available: bool
    product_errors: tuple[str, ...]
    research_errors: tuple[str, ...]

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


def evaluate_daily_close_preflight(
    *,
    branch: str | None,
    head: str | None,
    porcelain: str,
    repository_available: bool,
    catalog_available: bool,
) -> DailyClosePreflight:
    clean = not porcelain.strip()
    product_errors: list[str] = []
    research_errors: list[str] = []

    if not catalog_available:
        product_errors.append("m1_catalog_missing")
        research_errors.append("m1_catalog_missing")

    if not repository_available:
        research_errors.append("git_repository_unavailable")
    if not branch:
        research_errors.append(
            "named_branch_unavailable_or_detached_head"
        )
    if not head:
        research_errors.append("git_head_unavailable")
    if not clean:
        research_errors.append("worktree_not_clean")

    return DailyClosePreflight(
        product_lane_ready=not product_errors,
        research_lane_ready=not research_errors,
        branch=branch,
        head=head,
        worktree_clean=clean,
        repository_available=repository_available,
        catalog_available=catalog_available,
        product_errors=tuple(product_errors),
        research_errors=tuple(research_errors),
    )
