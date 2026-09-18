from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True, slots=True)
class DailyClosePreflight:
    passed: bool
    branch: str | None
    head: str | None
    worktree_clean: bool
    repository_available: bool
    catalog_available: bool
    errors: tuple[str, ...]

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
    errors: list[str] = []
    clean = not porcelain.strip()

    if not repository_available:
        errors.append("git_repository_unavailable")
    if not branch:
        errors.append("named_branch_unavailable_or_detached_head")
    if not head:
        errors.append("git_head_unavailable")
    if not clean:
        errors.append("worktree_not_clean")
    if not catalog_available:
        errors.append("m1_catalog_missing")

    return DailyClosePreflight(
        passed=not errors,
        branch=branch,
        head=head,
        worktree_clean=clean,
        repository_available=repository_available,
        catalog_available=catalog_available,
        errors=tuple(errors),
    )
