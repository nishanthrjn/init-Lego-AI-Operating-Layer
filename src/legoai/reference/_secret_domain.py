"""Private process-local ordering identity. No owner mutation wiring in this slice."""

import threading
from collections.abc import Iterator
from contextlib import contextmanager


class _OrderingDomain:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._holder: int | None = None

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
