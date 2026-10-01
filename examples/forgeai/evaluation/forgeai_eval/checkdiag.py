"""Content-free Ruff and pytest failure diagnostics (LQ1.2).

The input is the bounded stdout already held in ForgeAI's typed `CheckRecord`;
nothing is re-run. Only closed identifiers leave this module: Ruff rule codes
(`E501`, `I001`, ... or `invalid-syntax`) and pytest failure kinds. Paths,
source lines, messages, test names and tracebacks are never returned.

Patterns are pinned to the qualified check image (ruff 0.16.8, pytest 9.1.1)
and cross-checked against the tool's own totals (`Found N errors.`, `N failed,
M errors in ...`). Any mismatch or unrecognized structure yields
`unavailable`, never a guess.
"""

import re
from collections import Counter
from enum import StrEnum

from legoai_engineering.checks.errors import CheckFailure
from legoai_engineering.checks.values import CheckKind, CheckOutcome

from forgeai.domain import CheckRecord

RUFF_DIAGNOSTIC_UNAVAILABLE = "RUFF_DIAGNOSTIC_UNAVAILABLE"
PYTEST_DIAGNOSTIC_UNAVAILABLE = "PYTEST_DIAGNOSTIC_UNAVAILABLE"

_RUFF_RULE = re.compile(r"([A-Z]{1,4}[0-9]{1,4})(?: \[\*\])? \S.*")
_RUFF_NAMED = re.compile(r"(invalid-syntax): \S.*")
_RUFF_FOUND = re.compile(r"Found ([0-9]+) errors?\.")

_PYTEST_BLOCK = re.compile(r"=+ (FAILURES|ERRORS) =+")
_PYTEST_BANNER = re.compile(r"=+ .+ =+")
# Section headers are pytest-drawn; frame separators ("_ _ _") carry no name.
_PYTEST_SECTION = re.compile(r"_+ (.*[^_ ].*) _+")
_PYTEST_E_LINE = re.compile(r"E\s+(\S.*)")
_PYTEST_TOKEN = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*)(?::|$)")
_PYTEST_TOTALS = re.compile(r"=*\s*(.*?) in [0-9.]+s(?: \([^)]*\))?\s*=*")
_IMPORT_ERRORS = frozenset({"ImportError", "ModuleNotFoundError"})


class PytestKind(StrEnum):
    ASSERTION_FAILURE = "assertion_failure"
    DID_NOT_RAISE = "did_not_raise"
    EXCEPTION_FAILURE = "exception_failure"
    SETUP_ERROR = "setup_error"
    IMPORT_ERROR = "import_error"
    COLLECTION_ERROR = "collection_error"
    NO_TESTS = "no_tests"
    UNKNOWN_TEST_FAILURE = "unknown_test_failure"
    TIMEOUT = "timeout"
    INFRASTRUCTURE_ERROR = "infrastructure_error"
    PYTEST_ERROR = "pytest_error"


def _lines(output: bytes) -> list[str]:
    return output.decode("utf-8", "replace").splitlines()


def ruff_rules(stdout: bytes) -> dict[str, int] | None:
    """Rule-code counts of a failed `ruff check`, or None when unprovable."""
    lines = _lines(stdout)
    counts: Counter[str] = Counter()
    unrecognized = 0
    found: int | None = None
    for index, line in enumerate(lines):
        following = lines[index + 1] if index + 1 < len(lines) else ""
        if following.startswith(" --> "):
            match = _RUFF_RULE.fullmatch(line) or _RUFF_NAMED.fullmatch(line)
            if match is None:
                unrecognized += 1
            else:
                counts[match.group(1)] += 1
            continue
        total = _RUFF_FOUND.fullmatch(line)
        if total is not None:
            found = int(total.group(1))
    if found is None or found == 0 or unrecognized or sum(counts.values()) != found:
        return None
    return dict(sorted(counts.items()))


def _pytest_total(lines: list[str], word: str) -> int:
    for line in reversed(lines):
        match = _PYTEST_TOTALS.fullmatch(line)
        if match is not None:
            found = re.search(rf"([0-9]+) {word}", match.group(1))
            return int(found.group(1)) if found else 0
    return -1


def _section_kind(block: str, header: str, first: str | None) -> PytestKind:
    token_match = _PYTEST_TOKEN.match(first) if first is not None else None
    token = token_match.group(1) if token_match else None
    if block == "ERRORS":
        if header.startswith("ERROR collecting "):
            if token in _IMPORT_ERRORS:
                return PytestKind.IMPORT_ERROR
            return PytestKind.COLLECTION_ERROR
        if header.startswith(("ERROR at setup of ", "ERROR at teardown of ")):
            return PytestKind.SETUP_ERROR
        return PytestKind.UNKNOWN_TEST_FAILURE
    if first is None:
        return PytestKind.UNKNOWN_TEST_FAILURE
    if first.startswith("assert ") or token == "AssertionError":
        return PytestKind.ASSERTION_FAILURE
    if first.startswith("Failed: DID NOT RAISE"):
        return PytestKind.DID_NOT_RAISE
    if token is not None:
        return PytestKind.EXCEPTION_FAILURE
    return PytestKind.UNKNOWN_TEST_FAILURE


def pytest_kinds(stdout: bytes) -> dict[str, int] | None:
    """Failure-kind counts of a failed or interrupted `pytest -q` run."""
    lines = _lines(stdout)
    block: str | None = None
    sections: list[list[str | None]] = []  # [block, header, first E-line]
    current: list[str | None] | None = None
    for line in lines:
        opened = _PYTEST_BLOCK.fullmatch(line)
        if opened is not None:
            block, current = opened.group(1), None
            continue
        if _PYTEST_BANNER.fullmatch(line) or line.startswith("!!!"):
            block = current = None
            continue
        if block is None:
            continue
        header = _PYTEST_SECTION.fullmatch(line)
        if header is not None:
            current = [block, header.group(1), None]
            sections.append(current)
            continue
        if current is not None and current[2] is None:
            e_line = _PYTEST_E_LINE.fullmatch(line)
            if e_line is not None:
                current[2] = e_line.group(1)
    failures = sum(1 for section in sections if section[0] == "FAILURES")
    errors = len(sections) - failures
    if (
        not sections
        or failures != _pytest_total(lines, "failed")
        or errors != _pytest_total(lines, "errors?")
    ):
        return None
    counts = Counter(
        _section_kind(str(block_), str(header_), first).value
        for block_, header_, first in sections
    )
    return dict(sorted(counts.items()))


def check_diagnostic(record: CheckRecord) -> dict[str, object] | None:
    """Content-free detail for one failed Ruff-lint or pytest record, else None."""
    kind = record.request.kind
    if kind not in {CheckKind.RUFF_CHECK, CheckKind.PYTEST}:
        return None
    result = record.result
    if kind is CheckKind.RUFF_CHECK:
        if result is None or result.outcome is not CheckOutcome.FAILED:
            return None
        rules = ruff_rules(result.stdout)
        if rules is None:
            return {"status": RUFF_DIAGNOSTIC_UNAVAILABLE}
        return {"status": "classified", "rule_counts": rules}
    if result is None:
        if record.error is CheckFailure.TIMEOUT:
            return {
                "status": "classified",
                "kind_counts": {PytestKind.TIMEOUT.value: 1},
            }
        return {
            "status": "classified",
            "kind_counts": {PytestKind.INFRASTRUCTURE_ERROR.value: 1},
        }
    outcome = result.outcome
    if outcome is CheckOutcome.PASSED:
        return None
    if outcome is CheckOutcome.NO_TESTS:
        return {"status": "classified", "kind_counts": {PytestKind.NO_TESTS.value: 1}}
    if outcome is CheckOutcome.ERROR:
        return {
            "status": "classified",
            "kind_counts": {PytestKind.PYTEST_ERROR.value: 1},
        }
    kinds = pytest_kinds(result.stdout)
    if kinds is None:
        return {"status": PYTEST_DIAGNOSTIC_UNAVAILABLE}
    return {"status": "classified", "kind_counts": kinds}
