from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path


METHODOLOGY_CONTRACT_VERSION = 3

# Conservative file-level fingerprint for anything that can change candidate identity,
# Source Raw PRZ, canonical Source lifecycle, action-state interpretation, or M4
# prospective enrollment semantics. Infrastructure-only files are intentionally excluded.
METHODOLOGY_RELATIVE_PATHS: tuple[str, ...] = (
    "src/htcn/app/harmonic_service.py",
    "src/htcn/app/source_aligned_service.py",
    "src/htcn/app/source_clock_lifecycle_service.py",
    "src/htcn/app/decision_narrative.py",
    "src/htcn/data/adjustment.py",
    "src/htcn/harmonic/abcd.py",
    "src/htcn/harmonic/abcd_source.py",
    "src/htcn/harmonic/candidates.py",
    "src/htcn/harmonic/engine.py",
    "src/htcn/harmonic/evaluator.py",
    "src/htcn/harmonic/execution.py",
    "src/htcn/harmonic/five_zero.py",
    "src/htcn/harmonic/five_zero_source.py",
    "src/htcn/harmonic/indicators.py",
    "src/htcn/harmonic/lifecycle.py",
    "src/htcn/harmonic/models.py",
    "src/htcn/harmonic/pivots.py",
    "src/htcn/harmonic/prz.py",
    "src/htcn/harmonic/ratios.py",
    "src/htcn/harmonic/rsi_bamm.py",
    "src/htcn/harmonic/rsi_bamm_confluence.py",
    "src/htcn/harmonic/rsi_bamm_lifecycle.py",
    "src/htcn/harmonic/rules.py",
    "src/htcn/harmonic/scanner.py",
    "src/htcn/harmonic/shark.py",
    "src/htcn/harmonic/shark_source.py",
    "src/htcn/harmonic/source_lifecycle.py",
    "src/htcn/harmonic/source_prz.py",
    "src/htcn/harmonic/source_prz_evidence.py",
    "src/htcn/research/capture_transaction.py",
    "src/htcn/research/cohort_followup.py",
    "src/htcn/research/lifecycle_journal.py",
    "src/htcn/research/lifecycle_transitions.py",
    "src/htcn/research/methodology_identity.py",
    "src/htcn/research/prospective_observations.py",
    "src/htcn/research/snapshot_manifest.py",
    "scripts/m4_capture_lifecycle_snapshot.py",
)


@dataclass(frozen=True, slots=True)
class MethodologyIdentity:
    contract_version: int
    fingerprint: str
    component_count: int
    components: tuple[tuple[str, str], ...]

    def as_payload(self) -> dict[str, object]:
        payload = asdict(self)
        payload["components"] = [
            {"path": path, "sha256": digest}
            for path, digest in self.components
        ]
        return payload


def _project_root() -> Path:
    # .../src/htcn/research/methodology_identity.py -> repository root
    return Path(__file__).resolve().parents[3]


def build_methodology_identity(
    *,
    project_root: str | Path | None = None,
) -> MethodologyIdentity:
    root = _project_root() if project_root is None else Path(project_root)
    components: list[tuple[str, str]] = []
    for relative in METHODOLOGY_RELATIVE_PATHS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"methodology fingerprint source missing: {relative}"
            )
        digest = sha256(path.read_bytes()).hexdigest()
        components.append((relative, digest))

    material = "\n".join(
        f"{relative}:{digest}"
        for relative, digest in components
    )
    fingerprint = sha256(
        (
            f"contract={METHODOLOGY_CONTRACT_VERSION}\n"
            + material
        ).encode("utf-8")
    ).hexdigest()

    return MethodologyIdentity(
        contract_version=METHODOLOGY_CONTRACT_VERSION,
        fingerprint=fingerprint,
        component_count=len(components),
        components=tuple(components),
    )
