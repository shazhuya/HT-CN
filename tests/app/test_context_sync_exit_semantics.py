from pathlib import Path


def test_context_sync_degraded_is_nonblocking_exit_contract() -> None:
    source = Path("scripts/m3_sync_all_contexts.py").read_text(encoding="utf-8")
    assert 'overall in {"all_steps_completed", "degraded"}' in source
    assert 'else 2' in source
