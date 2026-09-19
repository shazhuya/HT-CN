from __future__ import annotations

import multiprocessing
import time
from pathlib import Path

from htcn.app.operator_process_lock import OperatorCacheProcessLock


def _hold_lock(
    path: str,
    acquired_queue,
    release_event,
) -> None:
    lock = OperatorCacheProcessLock(
        Path(path),
        timeout_seconds=5.0,
        poll_interval_seconds=0.02,
    )
    acquisition = lock.acquire()
    acquired_queue.put({
        "waited": acquisition.waited,
        "wait_seconds": acquisition.wait_seconds,
    })
    try:
        if not release_event.wait(timeout=5.0):
            raise RuntimeError("holder release timeout")
    finally:
        lock.release()


def _wait_for_lock(
    path: str,
    result_queue,
) -> None:
    lock = OperatorCacheProcessLock(
        Path(path),
        timeout_seconds=5.0,
        poll_interval_seconds=0.02,
    )
    acquisition = lock.acquire()
    try:
        result_queue.put({
            "waited": acquisition.waited,
            "wait_seconds": acquisition.wait_seconds,
            "lock_path": acquisition.lock_path,
        })
    finally:
        lock.release()


def test_operator_cache_process_lock_serializes_real_processes(
    tmp_path,
) -> None:
    ctx = multiprocessing.get_context("spawn")
    path = tmp_path / ".locks" / "operator-slot.lock"
    holder_ready = ctx.Queue()
    waiter_result = ctx.Queue()
    release_holder = ctx.Event()

    holder = ctx.Process(
        target=_hold_lock,
        args=(str(path), holder_ready, release_holder),
    )
    holder.start()
    holder_acquisition = holder_ready.get(timeout=5.0)
    assert holder_acquisition["waited"] is False

    waiter = ctx.Process(
        target=_wait_for_lock,
        args=(str(path), waiter_result),
    )
    waiter.start()

    time.sleep(0.20)
    assert waiter.is_alive(), (
        "second process should still be blocked on the same cache-slot lock"
    )

    release_holder.set()
    waiter_acquisition = waiter_result.get(timeout=5.0)

    holder.join(timeout=5.0)
    waiter.join(timeout=5.0)

    assert holder.exitcode == 0
    assert waiter.exitcode == 0
    assert waiter_acquisition["waited"] is True
    assert waiter_acquisition["wait_seconds"] >= 0.10
    assert waiter_acquisition["lock_path"] == str(path)
