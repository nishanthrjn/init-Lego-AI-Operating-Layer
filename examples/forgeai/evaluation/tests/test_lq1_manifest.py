"""LQ1 fixture manifest, revision identity and bounds."""

import json
import shutil
from pathlib import Path

import pytest
from eval_support import SENTINEL, fixture_set
from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
    digest_text,
)
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai_eval.fixtures import (
    EVALUATION,
    HIDDEN_ROOT,
    FixtureError,
    load_fixture_set,
)


def test_manifest_loads_with_verified_revisions() -> None:
    fixtures = fixture_set()
    assert fixtures.name == "forgeai-lq1"
    assert (fixtures.revision, fixtures.hidden_revision) == ("1", "1")
    assert [f.fixture_id for f in fixtures.fixtures] == [
        "stock-validation",
        "pager-boundaries",
        "temperature-units",
        "text-slug",
    ]
    assert len({f.category for f in fixtures.fixtures}) == 4
    assert all(f.fixture_digest.startswith("sha256:") for f in fixtures.fixtures)


@pytest.mark.parametrize("part", ["hidden", "template", "task"])
def test_changed_content_without_new_revision_is_refused(
    tmp_path: Path, part: str
) -> None:
    copy = tmp_path / "evaluation"
    shutil.copytree(
        EVALUATION,
        copy,
        ignore=shutil.ignore_patterns("__pycache__", "tests", "forgeai_eval"),
    )
    target = {
        "hidden": copy / "hidden/pager-boundaries/test_acceptance.py",
        "template": copy / "fixtures/pager-boundaries/repository/src/pager/pages.py",
        "task": copy / "fixtures/pager-boundaries/task.json",
    }[part]
    target.write_text(
        target.read_text(encoding="utf-8") + "\n# edited\n", encoding="utf-8"
    )
    with pytest.raises(FixtureError):
        load_fixture_set(copy / "manifest.json")


def test_fixtures_respect_forgeai_and_review_bounds() -> None:
    for item in fixture_set().fixtures:
        assert 1 <= len(item.task.targets) <= 8
        for path in item.template.rglob("*"):
            if path.is_file():
                assert len(path.read_bytes()) <= 8192, path
        assert not (item.template / HIDDEN_ROOT).exists()
        assert not item.hidden.is_relative_to(item.template)
        # The reference proposal is a valid Coding proposal for the task targets.
        document = json.loads(item.reference_proposal.read_text(encoding="utf-8"))
        targets = {t.path.value: t.operation for t in item.task.targets}
        changes = []
        for change in document["changes"]:
            assert targets[change["path"]] is FileChangeKind(change["operation"])
            current = item.template / change["path"]
            changes.append(
                FileChange(
                    RepositoryPath(change["path"]),
                    FileChangeKind(change["operation"]),
                    digest_text(current.read_text(encoding="utf-8"))
                    if current.exists()
                    else None,
                    change["content"],
                )
            )
            assert len(change["content"].encode("utf-8")) <= 4000
        CodingProposal(
            RepositoryChangeSet(tuple(changes)),
            document["summary"],
            tuple(c["reason"] for c in document["changes"]),
            tuple(document["risks"]),
            tuple(document["unknowns"]),
        )


def test_hidden_tests_are_marked_and_absent_from_templates() -> None:
    for item in fixture_set().fixtures:
        hidden = item.hidden_files()
        assert hidden and all(p.startswith(HIDDEN_ROOT + "/") for p in hidden)
        assert all(SENTINEL in text for text in hidden.values())
        for path in item.template.rglob("*"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                assert SENTINEL not in text
                assert "test_hidden_" not in text
        task = json.dumps(
            [
                item.task.objective,
                [t.path.value for t in item.task.targets],
                list(item.task.constraints),
            ]
        )
        assert SENTINEL not in task and HIDDEN_ROOT not in task
