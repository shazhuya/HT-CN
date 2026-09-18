from htcn.research.outcome_engine_identity import (
    OUTCOME_ENGINE_CONTRACT_VERSION,
    OUTCOME_ENGINE_RELATIVE_PATHS,
    build_outcome_engine_identity,
)


def test_outcome_engine_identity_is_deterministic(tmp_path) -> None:
    for relative in OUTCOME_ENGINE_RELATIVE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(relative, encoding="utf-8")

    first = build_outcome_engine_identity(project_root=tmp_path)
    second = build_outcome_engine_identity(project_root=tmp_path)

    assert first == second
    assert first.contract_version == OUTCOME_ENGINE_CONTRACT_VERSION
    assert first.component_count == len(OUTCOME_ENGINE_RELATIVE_PATHS)
    assert len(first.fingerprint) == 64
    assert [path for path, _ in first.components] == list(
        OUTCOME_ENGINE_RELATIVE_PATHS
    )


def test_outcome_engine_identity_changes_on_engine_code_change(tmp_path) -> None:
    for relative in OUTCOME_ENGINE_RELATIVE_PATHS:
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("stable", encoding="utf-8")

    before = build_outcome_engine_identity(project_root=tmp_path)
    changed = tmp_path / OUTCOME_ENGINE_RELATIVE_PATHS[1]
    changed.write_text("changed", encoding="utf-8")
    after = build_outcome_engine_identity(project_root=tmp_path)

    assert before.fingerprint != after.fingerprint


def test_outcome_engine_identity_fails_closed_on_missing_component(
    tmp_path,
) -> None:
    try:
        build_outcome_engine_identity(project_root=tmp_path)
    except FileNotFoundError as exc:
        assert "outcome engine fingerprint source missing" in str(exc)
    else:
        raise AssertionError("missing outcome engine component must fail closed")


def test_outcome_engine_v1_component_contract_is_small_and_separate() -> None:
    assert OUTCOME_ENGINE_CONTRACT_VERSION == 1
    assert len(OUTCOME_ENGINE_RELATIVE_PATHS) == 4
    assert set(OUTCOME_ENGINE_RELATIVE_PATHS) == {
        "src/htcn/research/outcome_protocol.py",
        "src/htcn/research/outcome_evaluator.py",
        "src/htcn/research/outcome_snapshot.py",
        "src/htcn/research/outcome_engine_identity.py",
    }
