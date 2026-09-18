from scripts.m3_sync_all_contexts import _is_external_source_error


def test_external_source_error_classifier_accepts_remote_disconnect() -> None:
    error = ConnectionError(
        "('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))"
    )
    assert _is_external_source_error(error) is True


def test_external_source_error_classifier_rejects_local_programming_error() -> None:
    assert _is_external_source_error(TypeError("bad local schema")) is False
