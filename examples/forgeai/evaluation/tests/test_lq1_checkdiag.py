"""LQ1.2 Ruff rule and pytest failure-kind extraction (content-free, cross-checked).

Fixture texts reproduce real ruff 0.16.8 / pytest 9.1.1 output from the
qualified image; test_lq1_diagnostics_docker.py checks the live image itself.
"""

import json

import pytest
from diag_support import PYTEST_COLLECTION, PYTEST_FAILED, RUFF_FAILED, SENTINEL
from legoai_engineering.checks.errors import CheckFailure
from legoai_engineering.checks.values import CheckKind, CheckRequest, CheckResult
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.domain import CheckRecord
from forgeai_eval.checkdiag import (
    PYTEST_DIAGNOSTIC_UNAVAILABLE,
    RUFF_DIAGNOSTIC_UNAVAILABLE,
    check_diagnostic,
    pytest_kinds,
    ruff_rules,
)


def record(
    kind: CheckKind,
    exit_code: int | None,
    stdout: str = "",
    error: CheckFailure | None = None,
) -> CheckRecord:
    request = CheckRequest(kind, (RepositoryPath("src"),))
    if exit_code is None:
        return CheckRecord(request, None, error)
    return CheckRecord(request, CheckResult(kind, exit_code, stdout.encode(), b""))


def test_ruff_rule_codes_are_extracted_and_reconciled() -> None:
    assert ruff_rules(RUFF_FAILED.encode()) == {
        "E501": 1,
        "F401": 1,
        "I001": 1,
        "invalid-syntax": 1,
    }


@pytest.mark.parametrize(
    "broken",
    [
        RUFF_FAILED.replace("Found 4 errors.", "Found 5 errors."),
        RUFF_FAILED.replace("Found 4 errors.\n", ""),
        RUFF_FAILED.replace("I001 [*] Import", "unknown-kind: Import"),
        "",
    ],
    ids=["total-mismatch", "no-total", "unrecognized-kind", "empty"],
)
def test_ruff_output_that_cannot_be_reconciled_is_unavailable(broken: str) -> None:
    assert ruff_rules(broken.encode()) is None


def test_pytest_failure_kinds_are_extracted_and_reconciled() -> None:
    assert pytest_kinds(PYTEST_FAILED.encode()) == {
        "assertion_failure": 1,
        "did_not_raise": 1,
        "exception_failure": 1,
        "setup_error": 1,
    }
    assert pytest_kinds(PYTEST_COLLECTION.encode()) == {"import_error": 1}


@pytest.mark.parametrize(
    "broken",
    [
        PYTEST_FAILED.replace("3 failed", "4 failed"),
        PYTEST_FAILED.replace("1 error in", "2 errors in"),
        PYTEST_FAILED.replace("3 failed, 1 passed, 1 error in 0.15s\n", ""),
        "",
    ],
    ids=["failed-mismatch", "error-mismatch", "no-totals", "empty"],
)
def test_pytest_output_that_cannot_be_reconciled_is_unavailable(broken: str) -> None:
    assert pytest_kinds(broken.encode()) is None


def test_check_records_map_to_content_free_details() -> None:
    assert check_diagnostic(record(CheckKind.RUFF_CHECK, 0)) is None
    assert check_diagnostic(record(CheckKind.MYPY, 1, "x")) is None  # not in LQ1.2
    assert check_diagnostic(record(CheckKind.RUFF_CHECK, 1, "garbage")) == {
        "status": RUFF_DIAGNOSTIC_UNAVAILABLE
    }
    assert check_diagnostic(record(CheckKind.PYTEST, 1, "garbage")) == {
        "status": PYTEST_DIAGNOSTIC_UNAVAILABLE
    }
    assert check_diagnostic(record(CheckKind.PYTEST, 5)) == {
        "status": "classified",
        "kind_counts": {"no_tests": 1},
    }
    assert check_diagnostic(record(CheckKind.PYTEST, 3)) == {
        "status": "classified",
        "kind_counts": {"pytest_error": 1},
    }
    timeout = record(CheckKind.PYTEST, None, error=CheckFailure.TIMEOUT)
    assert check_diagnostic(timeout) == {
        "status": "classified",
        "kind_counts": {"timeout": 1},
    }
    io = record(CheckKind.PYTEST, None, error=CheckFailure.IO)
    assert check_diagnostic(io) == {
        "status": "classified",
        "kind_counts": {"infrastructure_error": 1},
    }


def test_extracted_details_carry_no_tool_text() -> None:
    details = [
        check_diagnostic(record(CheckKind.RUFF_CHECK, 1, RUFF_FAILED)),
        check_diagnostic(record(CheckKind.PYTEST, 1, PYTEST_FAILED)),
        check_diagnostic(record(CheckKind.PYTEST, 2, PYTEST_COLLECTION)),
    ]
    text = json.dumps(details)
    for leaked in (
        SENTINEL,
        "Line too long",
        "src/pkg",
        "tests/test_a.py",
        "test_raises",
        "missing_module_xyz",
        "assert 1 == 2",
        "RuntimeError",
    ):
        assert leaked not in text, leaked
