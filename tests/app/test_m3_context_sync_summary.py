from scripts.m3_sync_all_contexts import _error


def test_combined_context_sync_error_is_machine_readable() -> None:
    assert _error(RuntimeError("boom")) == "RuntimeError: boom"
