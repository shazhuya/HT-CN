from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
from typing import Iterable, Sequence


DATA_INPUT_IDENTITY_CONTRACT_VERSION = 1
ANALYSIS_CODE_IDENTITY_CONTRACT_VERSION = 1
OPERATOR_INPUT_IDENTITY_CONTRACT_VERSION = 1

# Only finalized analysis inputs are included. Product-cache outputs are
# intentionally excluded to avoid self-invalidating cache identities.
DATA_INPUT_FILES: tuple[str, ...] = (
    "catalog.duckdb",
    "catalog.duckdb.wal",
)
DATA_INPUT_DIRECTORIES: tuple[str, ...] = (
    "daily",
    "daily_delta",
    "adjustment/qfq",
    "benchmarks",
)

# Conservative product-analysis dependency list. This is not the M4
# methodology contract. It exists only to invalidate the M5 product cache
# when code that can change Queue output changes.
ANALYSIS_APP_FILES: tuple[str, ...] = (
    "src/htcn/app/a_share_execution_context.py",
    "src/htcn/app/concept_context.py",
    "src/htcn/app/context_integrity.py",
    "src/htcn/app/decision_narrative.py",
    "src/htcn/app/harmonic_service.py",
    "src/htcn/app/market_context.py",
    "src/htcn/app/operator_input_identity.py",
    "src/htcn/app/operator_queue.py",
    "src/htcn/app/operator_snapshot.py",
    "src/htcn/app/sector_context.py",
    "src/htcn/app/source_aligned_service.py",
    "src/htcn/app/source_clock_lifecycle_service.py",
)
ANALYSIS_DATA_FILES: tuple[str, ...] = (
    "src/htcn/data/adjustment.py",
    "src/htcn/data/benchmarks.py",
    "src/htcn/data/concepts.py",
    "src/htcn/data/delta.py",
    "src/htcn/data/models.py",
    "src/htcn/data/sectors.py",
    "src/htcn/data/store.py",
    "src/htcn/data/symbols.py",
    "src/htcn/data/validation.py",
)
ANALYSIS_CODE_RECURSIVE_DIRS: tuple[str, ...] = (
    "src/htcn/harmonic",
)


@dataclass(frozen=True, slots=True)
class DataInputIdentity:
    contract_version: int
    fingerprint: str
    component_count: int
    manifest_mode: str = "relative_path_size_mtime_ns"

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class AnalysisCodeIdentity:
    contract_version: int
    fingerprint: str
    component_count: int
    manifest_mode: str = "relative_path_content_sha256"

    def as_payload(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class OperatorCacheInputIdentity:
    contract_version: int
    fingerprint: str
    data: DataInputIdentity
    analysis_code: AnalysisCodeIdentity

    def as_payload(self) -> dict[str, object]:
        return {
            "contract_version": self.contract_version,
            "fingerprint": self.fingerprint,
            "data": self.data.as_payload(),
            "analysis_code": self.analysis_code.as_payload(),
            "authoritative_evidence": False,
            "writes_m4_evidence": False,
            "methodology_identity": False,
        }


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _project_root() -> Path:
    # .../src/htcn/app/operator_input_identity.py -> repository root
    return Path(__file__).resolve().parents[3]


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _data_manifest(
    data_root: Path,
    *,
    file_paths: Sequence[str],
    directory_paths: Sequence[str],
) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []

    for relative in file_paths:
        path = data_root / relative
        if not path.is_file():
            entries.append({
                "path": relative,
                "kind": "missing_file",
                "size": None,
                "mtime_ns": None,
            })
            continue
        stat = path.stat()
        entries.append({
            "path": relative,
            "kind": "file",
            "size": int(stat.st_size),
            "mtime_ns": int(stat.st_mtime_ns),
        })

    for relative in directory_paths:
        root = data_root / relative
        if not root.is_dir():
            entries.append({
                "path": relative,
                "kind": "missing_directory",
                "size": None,
                "mtime_ns": None,
            })
            continue
        files = sorted(
            path
            for path in root.rglob("*.parquet")
            if path.is_file()
        )
        if not files:
            entries.append({
                "path": relative,
                "kind": "empty_directory",
                "size": 0,
                "mtime_ns": None,
            })
            continue
        for path in files:
            stat = path.stat()
            entries.append({
                "path": _relative(path, data_root),
                "kind": "file",
                "size": int(stat.st_size),
                "mtime_ns": int(stat.st_mtime_ns),
            })

    entries.sort(key=lambda item: (str(item["path"]), str(item["kind"])))
    return entries


def build_data_input_identity(
    data_root: str | Path,
    *,
    file_paths: Sequence[str] = DATA_INPUT_FILES,
    directory_paths: Sequence[str] = DATA_INPUT_DIRECTORIES,
) -> DataInputIdentity:
    root = Path(data_root)
    entries = _data_manifest(
        root,
        file_paths=file_paths,
        directory_paths=directory_paths,
    )
    material = {
        "contract_version": DATA_INPUT_IDENTITY_CONTRACT_VERSION,
        "manifest_mode": "relative_path_size_mtime_ns",
        "entries": entries,
    }
    fingerprint = sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    return DataInputIdentity(
        contract_version=DATA_INPUT_IDENTITY_CONTRACT_VERSION,
        fingerprint=fingerprint,
        component_count=len(entries),
    )


def default_analysis_code_paths(
    project_root: str | Path | None = None,
) -> tuple[str, ...]:
    root = _project_root() if project_root is None else Path(project_root)
    paths = {
        *ANALYSIS_APP_FILES,
        *ANALYSIS_DATA_FILES,
    }
    for relative_dir in ANALYSIS_CODE_RECURSIVE_DIRS:
        directory = root / relative_dir
        if not directory.is_dir():
            raise FileNotFoundError(
                f"operator analysis-code directory missing: {relative_dir}"
            )
        for path in directory.rglob("*.py"):
            if path.is_file():
                paths.add(_relative(path, root))
    return tuple(sorted(paths))


def build_analysis_code_identity(
    *,
    project_root: str | Path | None = None,
    relative_paths: Iterable[str] | None = None,
) -> AnalysisCodeIdentity:
    root = _project_root() if project_root is None else Path(project_root)
    paths = (
        tuple(sorted({str(value) for value in relative_paths}))
        if relative_paths is not None
        else default_analysis_code_paths(root)
    )
    components: list[tuple[str, str]] = []
    for relative in paths:
        path = root / relative
        if not path.is_file():
            raise FileNotFoundError(
                f"operator analysis-code fingerprint source missing: {relative}"
            )
        components.append(
            (relative, sha256(path.read_bytes()).hexdigest())
        )

    material = {
        "contract_version": ANALYSIS_CODE_IDENTITY_CONTRACT_VERSION,
        "manifest_mode": "relative_path_content_sha256",
        "components": components,
    }
    fingerprint = sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    return AnalysisCodeIdentity(
        contract_version=ANALYSIS_CODE_IDENTITY_CONTRACT_VERSION,
        fingerprint=fingerprint,
        component_count=len(components),
    )


def build_operator_cache_input_identity(
    *,
    data_root: str | Path,
    project_root: str | Path | None = None,
) -> OperatorCacheInputIdentity:
    data = build_data_input_identity(data_root)
    analysis_code = build_analysis_code_identity(
        project_root=project_root,
    )
    material = {
        "contract_version": OPERATOR_INPUT_IDENTITY_CONTRACT_VERSION,
        "data_contract_version": data.contract_version,
        "data_fingerprint": data.fingerprint,
        "analysis_code_contract_version": analysis_code.contract_version,
        "analysis_code_fingerprint": analysis_code.fingerprint,
    }
    fingerprint = sha256(
        _canonical_json(material).encode("utf-8")
    ).hexdigest()
    return OperatorCacheInputIdentity(
        contract_version=OPERATOR_INPUT_IDENTITY_CONTRACT_VERSION,
        fingerprint=fingerprint,
        data=data,
        analysis_code=analysis_code,
    )
