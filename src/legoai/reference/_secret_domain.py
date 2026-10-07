"""Private process-local ordering identity. Explicit participation; no owner state or public locking API."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager


class _OrderingDomain:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._holder: int | None = None

    @staticmethod
    def thread_identity() -> int:
        return threading.get_ident()

    def outside(self) -> None:
        if self._holder == threading.get_ident():
            raise RuntimeError("operation forbidden inside acceptance domain")

    def held(self) -> None:
        if self._holder != threading.get_ident():
            raise RuntimeError("acceptance domain required")

    @contextmanager
    def enter(self) -> Iterator[None]:
        self.outside()
        with self._lock:
            self._holder = threading.get_ident()
            try:
                yield
            finally:
                self._holder = None
