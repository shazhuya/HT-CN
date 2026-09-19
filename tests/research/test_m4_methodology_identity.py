from hashlib import sha256

from htcn.research.methodology_identity import (
    METHODOLOGY_CONTRACT_VERSION,
    METHODOLOGY_RELATIVE_PATHS,
    build_methodology_identity,
)


def test_methodology_identity_is_deterministic_and_component_ordered(tmp_path) -> None:
    for relative in METHODOLOGY_RELATIVE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")

    first = build_methodology_identity(project_root=tmp_path)
    second = build_methodology_identity(project_root=tmp_path)

    assert first == second
    assert first.contract_version == METHODOLOGY_CONTRACT_VERSION
    assert first.component_count == len(METHODOLOGY_RELATIVE_PATHS)
    assert len(first.fingerprint) == 64
    assert [path for path, _ in first.components] == list(
        METHODOLOGY_RELATIVE_PATHS
    )


def test_methodology_identity_changes_when_core_method_file_changes(tmp_path) -> None:
    for relative in METHODOLOGY_RELATIVE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stable", encoding="utf-8")

    first = build_methodology_identity(project_root=tmp_path)
    changed = tmp_path / METHODOLOGY_RELATIVE_PATHS[0]
    changed.write_text("changed", encoding="utf-8")
    second = build_methodology_identity(project_root=tmp_path)

    assert first.fingerprint != second.fingerprint


def test_methodology_identity_fails_closed_on_missing_component(tmp_path) -> None:
    try:
        build_methodology_identity(project_root=tmp_path)
    except FileNotFoundError as exc:
        assert "methodology fingerprint source missing" in str(exc)
    else:
        raise AssertionError("missing methodology component must fail closed")


def test_methodology_identity_covers_advanced_harmonic_state_files() -> None:
    required = {
        "src/htcn/harmonic/five_zero_source.py",
        "src/htcn/harmonic/indicators.py",
        "src/htcn/harmonic/lifecycle.py",
        "src/htcn/harmonic/rsi_bamm.py",
        "src/htcn/harmonic/rsi_bamm_confluence.py",
        "src/htcn/harmonic/rsi_bamm_lifecycle.py",
        "src/htcn/harmonic/source_lifecycle.py",
        "src/htcn/research/capture_transaction.py",
        "src/htcn/research/cohort_followup.py",
        "src/htcn/research/lifecycle_transitions.py",
        "src/htcn/research/prospective_observations.py",
        "src/htcn/research/snapshot_manifest.py",
        "scripts/m4_capture_lifecycle_snapshot.py",
    }
    assert required.issubset(set(METHODOLOGY_RELATIVE_PATHS))



def test_methodology_v4_covers_prospective_evidence_semantics() -> None:
    assert METHODOLOGY_CONTRACT_VERSION == 4
    assert len(METHODOLOGY_RELATIVE_PATHS) == 37
    required = {
        "src/htcn/research/capture_transaction.py",
        "src/htcn/research/cohort_followup.py",
        "src/htcn/research/lifecycle_journal.py",
        "src/htcn/research/lifecycle_transitions.py",
        "src/htcn/research/prospective_observations.py",
        "src/htcn/research/snapshot_manifest.py",
        "scripts/m4_capture_lifecycle_snapshot.py",
    }
    assert required.issubset(set(METHODOLOGY_RELATIVE_PATHS))
