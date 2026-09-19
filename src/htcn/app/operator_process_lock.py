from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

if os.name == "nt":
    import msvcrt
else:
    import fcntl


@dataclass(frozen=True, slots=True)
class ProcessLockAcquisition:
    waited: bool
    wait_seconds: float
    lock_path: str


class OperatorCacheProcessLock:
    """Cross-process advisory lock for one Operator cache slot.

    The lock is execution-only. It does not own Queue semantics, candidate
    identity, lifecycle, or M4 evidence. OS advisory locking is used so a
    crashed owner releases the lock when its file descriptor is closed by the
    operating system.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        timeout_seconds: float = 1800.0,
        poll_interval_seconds: float = 0.05,
    ) -> None:
        self.path = Path(path)
        self.timeout_seconds = max(0.0, float(timeout_seconds))
        self.poll_interval_seconds = max(
            0.01,
            float(poll_interval_seconds),
        )
        self._handle: BinaryIO | None = None
        self._locked = False

    def _try_lock(self, handle: BinaryIO) -> bool:
        if os.name == "nt":
            handle.seek(0)
            try:
                msvcrt.locking(
                    handle.fileno(),
                    msvcrt.LK_NBLCK,
                    1,
                )
                return True
            except OSError:
                return False
        try:
            fcntl.flock(
                handle.fileno(),
                fcntl.LOCK_EX | fcntl.LOCK_NB,
            )
            return True
        except BlockingIOError:
            return False

    def acquire(self) -> ProcessLockAcquisition:
        if self._locked:
            raise RuntimeError("operator cache process lock already acquired")

        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle = self.path.open("a+b", buffering=0)
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"\0")
            handle.flush()
        handle.seek(0)

        started = time.monotonic()
        waited = False
        try:
            while True:
                if self._try_lock(handle):
                    self._handle = handle
                    self._locked = True
                    return ProcessLockAcquisition(
                        waited=waited,
                        wait_seconds=max(
                            0.0,
                            time.monotonic() - started,
                        ),
                        lock_path=str(self.path),
                    )
                waited = True
                elapsed = time.monotonic() - started
                if elapsed >= self.timeout_seconds:
                    raise TimeoutError(
                        "operator cache cross-process lock timeout: "
                        f"{self.path}"
                    )
                time.sleep(
                    min(
                        self.poll_interval_seconds,
                        max(0.0, self.timeout_seconds - elapsed),
                    )
                )
        except BaseException:
            handle.close()
            raise

    def release(self) -> None:
        handle = self._handle
        if handle is None or not self._locked:
            return
        try:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(
                    handle.fileno(),
                    msvcrt.LK_UNLCK,
                    1,
                )
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            self._locked = False
            self._handle = None
            handle.close()
