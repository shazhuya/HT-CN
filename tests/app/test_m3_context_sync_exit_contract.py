from scripts.m3_sync_all_contexts import _error


def test_context_sync_uses_same_success_literal_for_summary_and_exit_contract() -> None:
    import inspect

    import scripts.m3_sync_all_contexts as module

    source = inspect.getsource(module.main)
    assert '"all_steps_completed"' in source
    assert '"complete"' not in source
    assert 'return 0 if overall in {"all_steps_completed", "degraded"} else 2' in source


def test_context_sync_error_formatter_remains_stable() -> None:
    assert _error(RuntimeError("boom")) == "RuntimeError: boom"
