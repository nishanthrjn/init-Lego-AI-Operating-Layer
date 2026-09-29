"""Hidden-test isolation: the oracle never reaches ForgeAI, its Agents or inputs.

Instrumented at the real boundaries: the replay ModelPort records every model
request, and recording sandboxes capture every file ForgeAI's checks and the
oracle send into a sandbox. Names alone are not trusted; a sentinel string
that exists only inside hidden tests is searched for everywhere.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest
from eval_support import (
    REVIEW_ACCEPT,
    SENTINEL,
    fixture,
    fixture_set,
    reference,
    replay_settings,
)
from forgeai_support import git_executable, snapshot

from forgeai.cli import ReplayModel, replay_binding
from forgeai.composition import local_profile
from forgeai_eval.fixtures import HIDDEN_ROOT, provision
from forgeai_eval.hidden import HiddenOutcome
from forgeai_eval.runner import evaluate_run


@pytest.mark.parametrize(
    "fixture_id",
    ["stock-validation", "pager-boundaries", "temperature-units", "text-slug"],
)
def test_hidden_tests_never_enter_forgeai(tmp_path: Path, fixture_id: str) -> None:
    item = fixture(fixture_id)
    hidden_texts = list(item.hidden_files().values())
    log: list[str] = []
    settings, model, forge, hidden = replay_settings(
        tmp_path, (reference(item), REVIEW_ACCEPT), log=log
    )
    run = evaluate_run(item, 1, settings)
    assert run.task_result.disposition.value == "succeeded"
    assert run.hidden.outcome is HiddenOutcome.PASSED

    # Repository after the run: no hidden directory, file or content.
    files = snapshot(tmp_path / f"{fixture_id}-1")
    assert not any(path.split("/")[0] == HIDDEN_ROOT for path in files)
    assert not any(SENTINEL.encode() in data for data in files.values())

    # Every model request is free of hidden content. Authorized Coding reads
    # and review materials reach the models only through these requests.
    assert len(model.requests) == 2
    for request in model.requests:
        for message in request.messages:
            assert SENTINEL not in message.content
            assert "test_hidden_" not in message.content
            assert all(text not in message.content for text in hidden_texts)

    # Review materials recorded in evidence are free of hidden content.
    review = run.task_result.evidence.review
    assert review is not None
    assert all(SENTINEL not in m.text for m in review.request.evidence)
    assert SENTINEL not in review.request.proposal
    assert all(
        HIDDEN_ROOT not in path.value
        for _, path in run.task_result.evidence.review_materials
    )

    # ForgeAI's own sandbox inputs never include hidden tests...
    assert forge.requests
    for sandbox_request in forge.requests:
        for file in sandbox_request.files:
            assert not file.path.startswith(HIDDEN_ROOT)
            assert SENTINEL not in file.text
    # ...while the oracle's single sandbox call does, strictly after ForgeAI.
    assert len(hidden.requests) == 1
    oracle_paths = [file.path for file in hidden.requests[0].files]
    assert f"{HIDDEN_ROOT}/test_acceptance.py" in oracle_paths
    last_forgeai = max(i for i, name in enumerate(log) if name == "forgeai-check")
    assert log.index("hidden-check") > last_forgeai
    assert log[-1] == "hidden-check" and log.count("hidden-check") == 1


def test_targets_allowlist_and_check_inputs_exclude_the_hidden_root(
    tmp_path: Path,
) -> None:
    for item in fixture_set().fixtures:
        repo = provision(item, tmp_path / item.fixture_id, git_executable())
        # The harness builds ForgeAI's configuration exactly like this.
        config = local_profile(
            repo,
            tuple(target.path for target in item.task.targets),
            bindings=(replay_binding(ReplayModel("unused")),),
            binding="replay",
            git_executable=git_executable(),
            docker_executable=git_executable(),
            now=datetime.now(UTC),
        )
        allowed = [path.value for path in config.editable_paths]
        roots = [path.value for path in config.check_inputs.roots]
        inputs = [path.value for path in config.check_inputs.files]
        planned = [path.value for c in config.check_plan for path in c.targets]
        for values in (allowed, roots, inputs, planned):
            assert not any(v.split("/")[0] == HIDDEN_ROOT for v in values), values
        assert allowed == [target.path.value for target in item.task.targets]


def test_provisioned_repository_starts_without_hidden_material(tmp_path: Path) -> None:
    for item in fixture_set().fixtures:
        repo = provision(item, tmp_path / item.fixture_id, git_executable())
        files = snapshot(repo)
        assert not any(path.startswith(HIDDEN_ROOT) for path in files)
        assert not any(SENTINEL.encode() in data for data in files.values())
