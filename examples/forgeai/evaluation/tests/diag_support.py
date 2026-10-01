"""LQ1.2 test data: deterministic replies for every reachable diagnostic category.

These are test fixtures only; nothing here reaches a live prompt.
"""

import base64
import copy
import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

from eval_support import REVIEW_ACCEPT, fixture, reference
from forgeai_support import FakeSandbox, git_executable
from legoai.runtime.api import ModelBindingConfig
from legoai_engineering.repository.mutation import (
    ContentDigest,
    FileChangeKind,
    digest_text,
)
from legoai_engineering.sandbox.ports import CancellationSignal
from legoai_engineering.sandbox.values import SandboxRequest, SandboxResult

from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.fixtures import Fixture
from forgeai_eval.observer import ObservationLog, ObservingModel
from forgeai_eval.outputs import CodingDiagnostic as C
from forgeai_eval.outputs import ReviewDiagnostic as R
from forgeai_eval.runner import RunSettings

SENTINEL = "lq12-sentinel-must-not-leak"


def _variant(good: str) -> Callable[..., str]:
    base = json.loads(good)

    def variant(
        edit: Callable[[dict[str, object]], object] | None = None, **fields: object
    ) -> str:
        value = copy.deepcopy(base)
        value.update(fields)
        if edit is not None:
            edit(value)
        return json.dumps(value)

    return variant


def _change(**fields: object) -> Callable[[dict[str, object]], None]:
    def edit(value: dict[str, object]) -> None:
        changes = value["changes"]
        assert isinstance(changes, list)
        changes[0].update(fields)

    return edit


def _drop(container: str, key: str) -> Callable[[dict[str, object]], None]:
    def edit(value: dict[str, object]) -> None:
        if container == "top":
            del value[key]
        else:
            changes = value["changes"]
            assert isinstance(changes, list)
            del changes[0][key]

    return edit


def coding_samples() -> dict[str, tuple[str, C]]:
    """stock-validation replies (two UPDATE targets): id -> (reply, category)."""
    good = reference(fixture("stock-validation"))
    v = _variant(good)
    first = json.loads(good)["changes"][0]
    return {
        "valid": (good, C.VALID),
        "blank": ("   \n", C.OUTPUT_TEXT_INVALID),
        "over-output-limit": ("x" * 40_000, C.OUTPUT_LIMIT),
        "prose": (f"I updated the module. {SENTINEL}", C.RESPONSE_NOT_JSON),
        "fenced-json": ("```json\n" + good + "\n```", C.RESPONSE_NOT_JSON),
        "duplicate-key": (
            '{"summary":"dup",' + good.lstrip()[1:],
            C.DUPLICATE_JSON_KEY,
        ),
        "top-level-array": (json.dumps([json.loads(good)]), C.TOP_LEVEL_NOT_OBJECT),
        "missing-field": (v(_drop("top", "risks")), C.TOP_LEVEL_FIELDS_INVALID),
        "unexpected-field": (v(files=[]), C.TOP_LEVEL_FIELDS_INVALID),
        "changes-not-array": (v(changes={}), C.CHANGES_NOT_BOUNDED_ARRAY),
        "change-not-object": (v(changes=["x"]), C.CHANGE_ENTRY_NOT_OBJECT),
        "change-missing-reason": (
            v(_drop("change", "reason")),
            C.CHANGE_FIELDS_INVALID,
        ),
        "bad-path": (v(_change(path="src/inventory/st?ck.py")), C.PATH_INVALID),
        "path-not-text": (v(_change(path=7)), C.PATH_INVALID),
        "path-outside-targets": (
            v(_change(path="src/inventory/other.py")),
            C.PATH_NOT_REQUESTED_TARGET,
        ),
        "invalid-operation": (v(_change(operation="modify")), C.OPERATION_INVALID),
        "operation-mismatch": (
            v(_change(operation="create")),
            C.OPERATION_TARGET_MISMATCH,
        ),
        "content-not-text": (v(_change(content=7)), C.CONTENT_INVALID),
        "content-nul": (v(_change(content="a\u0000b")), C.CONTENT_INVALID),
        "reason-not-text": (v(_change(reason=7)), C.REASON_INVALID),
        "reason-blank": (v(_change(reason=" ")), C.REASON_INVALID),
        "changes-empty": (v(changes=[]), C.CHANGES_EMPTY),
        "duplicate-target": (v(changes=[first, first]), C.DUPLICATE_CHANGE_TARGET),
        "summary-not-text": (v(summary=7), C.SUMMARY_INVALID),
        "summary-blank": (v(summary=" "), C.SUMMARY_INVALID),
        "risks-not-array": (v(risks="none"), C.NARRATIVE_INVALID),
        "risk-blank": (v(risks=[""]), C.NARRATIVE_INVALID),
        "content-limit": (
            v(_change(content=f"# {SENTINEL}\n" + "x = 1\n" * 1600)),
            C.CONTENT_LIMIT,
        ),
    }


def create_samples() -> dict[str, tuple[str, C]]:
    """text-slug replies (two CREATE targets)."""
    good = reference(fixture("text-slug"))
    v = _variant(good)
    return {
        "create-valid": (good, C.VALID),
        "create-as-update": (
            v(_change(operation="update")),
            C.OPERATION_TARGET_MISMATCH,
        ),
    }


def review_samples() -> dict[str, tuple[str, R]]:
    v = _variant(REVIEW_ACCEPT)
    bad_finding = {
        "category": "style",
        "severity": "info",
        "message": "m",
        "evidence_refs": ["proposal"],
        "required_action": None,
    }
    return {
        "valid": (REVIEW_ACCEPT, R.VALID),
        "blank": (" ", R.OUTPUT_TEXT_INVALID),
        "over-output-limit": ("x" * 17_000, R.OUTPUT_LIMIT),
        "fenced-json": ("```json\n" + REVIEW_ACCEPT + "\n```", R.RESPONSE_NOT_JSON),
        "missing-field": (v(_drop("top", "risks")), R.SCHEMA_INVALID),
        "finding-invalid": (v(findings=[bad_finding]), R.FINDING_INVALID),
        "decision-invalid": (v(decision="approve"), R.DECISION_INVALID),
        "decision-inconsistent": (
            v(decision="changes_required"),
            R.DECISION_INCONSISTENT,
        ),
    }


# Real ruff 0.16.8 / pytest 9.1.1 output shapes from the qualified image.
RUFF_FAILED = f"""E501 Line too long (101 > 88)
 --> src/pkg/mod.py:4:89
  |
4 |     return x + 1  # {SENTINEL}
  |                                                                                         ^^^^
  |

invalid-syntax: Expected a parameter or the end of the parameter list
 --> src/pkg/mod.py:5:7
  |
5 | def g(:
  |       ^

I001 [*] Import block is un-sorted or un-formatted
 --> tests/test_a.py:1:1
  |
1 | / import pytest
2 | | from pkg.ok import h
  | |____________________^
  |
help: Organize imports

F401 [*] `{SENTINEL}` imported but unused
 --> tests/test_b.py:1:8
  |
1 | import {SENTINEL}
  |        ^^^^^^^^^^^^^^^^^^
help: Remove unused import: `{SENTINEL}`

Found 4 errors.
[*] 2 fixable with the `--fix` option.
"""

PYTEST_FAILED = f"""
==================================== ERRORS ====================================
________________________ ERROR at setup of test_fixture ________________________

    @pytest.fixture
    def broken():
>       raise RuntimeError("fixture")
E       RuntimeError: fixture

tests/test_a.py:13: RuntimeError
=================================== FAILURES ===================================
_ test_assert_with_a_rather_long_name_to_trigger_terminal_truncation_in_summary _

    def test_assert_with_a_rather_long_name_to_trigger_terminal_truncation_in_summary():
>       assert h(1) == 2
E       assert 1 == 2
E        +  where 1 = h(1)

tests/test_a.py:4: AssertionError
_________________________________ test_raises __________________________________

    def test_raises():
>       with pytest.raises(ValueError):
E       Failed: DID NOT RAISE ValueError

tests/test_a.py:6: Failed
___________________________________ test_exc ___________________________________

    def test_exc():
        print("E   assert spoof")
>       raise KeyError("{SENTINEL}")
E       KeyError: '{SENTINEL}'

tests/test_a.py:10: KeyError
----------------------------- Captured stdout call -----------------------------
E   assert spoof
=========================== short test summary info ============================
FAILED tests/test_a.py::test_assert_with_a_rather_long_name_to_trigger_terminal_truncation_in_summary
FAILED tests/test_a.py::test_raises - Failed: DID NOT RAISE ValueError
FAILED tests/test_a.py::test_exc - KeyError: '{SENTINEL}'
ERROR tests/test_a.py::test_fixture - RuntimeError: fixture
3 failed, 1 passed, 1 error in 0.15s
"""

PYTEST_COLLECTION = """
==================================== ERRORS ====================================
_______________________ ERROR collecting tests/test_b.py _______________________
ImportError while importing test module '/w/tests/test_b.py'.
Hint: make sure your test modules/packages have valid Python names.
Traceback:
tests/test_b.py:1: in <module>
    import missing_module_xyz
E   ModuleNotFoundError: No module named 'missing_module_xyz'
=========================== short test summary info ============================
ERROR tests/test_b.py
!!!!!!!!!!!!!!!!!!!! Interrupted: 1 error during collection !!!!!!!!!!!!!!!!!!!!
1 error in 0.22s
"""


class ScriptedSandbox(FakeSandbox):
    """Fake check sandbox whose calls return scripted (exit, stdout) pairs."""

    def __init__(self, script: tuple[tuple[int, str], ...]) -> None:
        super().__init__()
        self.script = script

    def execute(
        self, request: SandboxRequest, cancellation: CancellationSignal | None = None
    ) -> SandboxResult:
        exit_code, stdout = self.script[self.calls % len(self.script)]
        self.calls += 1
        body = {
            "status": "completed",
            "exit": exit_code,
            "stdout": base64.b64encode(stdout.encode()).decode("ascii"),
            "stderr": base64.b64encode(SENTINEL.encode()).decode("ascii"),
        }
        return SandboxResult(0, json.dumps(body).encode(), b"")


def observed_settings(
    workdir: Path,
    outputs: tuple[str | Exception, ...],
    script: tuple[tuple[int, str], ...] | None = None,
) -> tuple[RunSettings, ObservationLog]:
    """Replay settings whose model is observed by ObservingModel."""
    log = ObservationLog()
    model = ReplayModel(*outputs)

    def bindings(item: Fixture) -> tuple[tuple[ModelBindingConfig, ...], str]:
        return (replay_binding(ObservingModel(model, log)),), "replay"

    hidden = FakeSandbox()
    settings = RunSettings(
        bindings=bindings,
        git=git_executable(),
        docker=git_executable(),
        workdir=workdir,
        forgeai_sandbox=ScriptedSandbox(script) if script else FakeSandbox(),
        hidden_sandbox=lambda: hidden,
        observations=log,
        observation_wait_seconds=1.0,
    )
    return settings, log


def targets_of(
    fixture_id: str,
) -> dict[str, tuple[FileChangeKind, ContentDigest | None]]:
    """The targets ForgeAI supplies for a fixture, as the CodingAgent sees them."""
    item = fixture(fixture_id)
    found: dict[str, tuple[FileChangeKind, ContentDigest | None]] = {}
    for target in item.task.targets:
        path = item.template / target.path.value
        found[target.path.value] = (
            target.operation,
            digest_text(path.read_text(encoding="utf-8"))
            if target.operation is FileChangeKind.UPDATE
            else None,
        )
    return found


def part(diagnostics: dict[str, object], name: str) -> list[dict[str, Any]]:
    """Typed access to one list of a run's diagnostics record."""
    value = diagnostics[name]
    assert isinstance(value, list)
    return value
