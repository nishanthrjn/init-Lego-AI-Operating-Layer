"""LQ1.2 check diagnostics against the real qualified check image (no skip).

A replayed proposal with an unused import and a wrong assertion runs through
ForgeAI's real sandboxed checks; the Ruff and pytest extractors must classify
the image's actual output rather than report it unavailable.
"""

import json
import os
import shutil
from pathlib import Path

import pytest
from diag_support import part
from eval_support import fixture, reference
from forgeai_support import approve, git_executable
from legoai.runtime.api import ModelBindingConfig

from forgeai.cli import ReplayModel, replay_binding
from forgeai_eval.diagnostics import run_diagnostics
from forgeai_eval.fixtures import Fixture
from forgeai_eval.observer import ObservationLog, ObservingModel
from forgeai_eval.runner import RunSettings, evaluate_run

pytestmark = pytest.mark.skipif(
    os.name != "nt", reason="Windows Desktop reference scope"
)


def broken_proposal() -> str:
    value = json.loads(reference(fixture("stock-validation")))
    source, tests = value["changes"]
    source["content"] = "import os\n" + source["content"]
    tests["content"] = tests["content"].replace(
        "assert reserve(10, 3) == 7", "assert reserve(10, 3) == 8"
    )
    return json.dumps(value)


def test_real_ruff_and_pytest_output_is_classified(tmp_path: Path) -> None:
    executable = shutil.which("docker")
    assert executable is not None, "LQ1.2 Docker tests require Docker; no skip"
    log = ObservationLog()
    # Check findings request another coding proposal, never reviewer JSON.
    rework = json.loads(broken_proposal())
    for change in rework["changes"]:
        change["operation"] = "update"
    model = ReplayModel(broken_proposal(), json.dumps(rework))

    def bindings(item: Fixture) -> tuple[tuple[ModelBindingConfig, ...], str]:
        return (replay_binding(ObservingModel(model, log)),), "replay"

    settings = RunSettings(
        approve=approve,
        bindings=bindings,
        git=git_executable(),
        docker=Path(executable),
        workdir=tmp_path,
        observations=log,
    )
    run = evaluate_run(fixture("stock-validation"), 1, settings)
    assert run.task_result.failure is not None
    assert run.task_result.failure.name == "CHECKS_FAILED"
    assert model.calls == 2
    assert len(run.task_result.evidence.attempts) == 2
    assert all(attempt.review is None for attempt in run.task_result.evidence.attempts)
    checks = {e["kind"]: e for e in part(run_diagnostics(run), "checks")}
    ruff = checks["ruff_check"]
    assert ruff["status"] == "classified", ruff
    assert ruff["rule_counts"]["F401"] == 1
    pytest_detail = checks["pytest"]
    assert pytest_detail["status"] == "classified", pytest_detail
    assert pytest_detail["kind_counts"] == {"assertion_failure": 1}
