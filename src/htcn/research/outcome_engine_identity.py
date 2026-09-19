from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

OUTCOME_ENGINE_CONTRACT_VERSION = 1

# Outcome semantics are versioned independently from capture methodology.
# The capture methodology fingerprint already owns harmonic/source-clock core files.
# This conservative set freezes the implementation that transforms frozen enrollment
# evidence + market paths into outcome facts and immutable outcome snapshots.
OUTCOME_ENGINE_RELATIVE_PATHS: tuple[str, ...] = (
    "src/htcn/research/outcome_protocol.py",
    "src/htcn/research/outcome_evaluator.py",
    "src/htcn/research/outcome_snapshot.py",
    "src/htcn/research/outcome_engine_identity.py",
)


@dataclass(frozen=True, slots=True)
class OutcomeEngineIdentity:
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
    return Path(__file__).resolve().parents[3]


def build_outcome_engine_identity(
    *,
    project_root: str | Path | None = None,
) -> OutcomeEngineIdentity:
    root = _project_root() if project_root is None else Path(project_root)
    components: list[tuple[str, str]] = []
    for relative in OUTCOME_ENGINE_RELATIVE_PATHS:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"outcome engine fingerprint source missing: {relative}"
            )
        digest = sha256(path.read_bytes()).hexdigest()
        components.append((relative, digest))

    material = "\n".join(
        f"{relative}:{digest}"
        for relative, digest in components
    )
    fingerprint = sha256(
        (
            f"contract={OUTCOME_ENGINE_CONTRACT_VERSION}\n"
            + material
        ).encode("utf-8")
    ).hexdigest()
    return OutcomeEngineIdentity(
        contract_version=OUTCOME_ENGINE_CONTRACT_VERSION,
        fingerprint=fingerprint,
        component_count=len(components),
        components=tuple(components),
    )
