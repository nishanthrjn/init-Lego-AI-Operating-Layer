"""Shared fixture-file access for document.parsing tests.

Fixture bytes live under tests/fixtures/parsing/ -- copied verbatim from the
design-time live-verification evidence in
planning/documind/parsing-verification/fixtures/ so this package's test
suite is self-contained and does not depend on the planning/ tree at test
time (mirrors the general rule that production/test infrastructure should
not depend on documentation trees that could move independently).
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest

_FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "parsing"


@pytest.fixture
def fixture_bytes() -> Callable[[str], bytes]:
    def _load(name: str) -> bytes:
        return (_FIXTURES_DIR / name).read_bytes()

    return _load
