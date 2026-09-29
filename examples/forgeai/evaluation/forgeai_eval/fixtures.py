"""Frozen fixture set: manifest, revision digests and repository provisioning.

A fixture is a template repository plus an operator task. Hidden acceptance
tests live in a separate tree and are never copied into a provisioned
repository. Digests normalize line endings so a Git checkout's CRLF
conversion does not change a revision's identity.
"""

import hashlib
import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from legoai_engineering.coding.values import CodingTarget
from legoai_engineering.repository.mutation import FileChangeKind
from legoai_engineering.repository.workspace import RepositoryPath

from forgeai.domain import TaskRequest

EVALUATION = Path(__file__).resolve().parents[1]
MANIFEST = EVALUATION / "manifest.json"
HIDDEN_ROOT = "acceptance"  # the virtual sandbox directory for hidden tests


class FixtureError(ValueError):
    """The fixture set does not match its manifest or bounds."""


def tree_digest(root: Path) -> str:
    """SHA-256 over sorted relative paths and LF-normalized UTF-8 contents."""
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        relative_parts = path.relative_to(root).parts
        if any(
            part == "__pycache__" or part.startswith(".") for part in relative_parts
        ):
            continue  # caches and tool state are not fixture content
        relative = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
        digest.update(relative.encode("utf-8") + b"\0" + text.encode("utf-8") + b"\0")
    return "sha256:" + digest.hexdigest()


@dataclass(frozen=True, slots=True)
class Fixture:
    fixture_id: str
    category: str
    task: TaskRequest
    template: Path
    hidden: Path
    reference_proposal: Path
    fixture_digest: str
    hidden_digest: str

    def hidden_files(self) -> dict[str, str]:
        """Hidden test files keyed by their virtual sandbox path."""
        return {
            f"{HIDDEN_ROOT}/{path.name}": path.read_text(encoding="utf-8")
            for path in sorted(self.hidden.glob("*.py"))
        }


@dataclass(frozen=True, slots=True)
class FixtureSet:
    name: str
    revision: str
    hidden_revision: str
    fixtures: tuple[Fixture, ...]

    @property
    def fixture_digest(self) -> str:
        return _combined(f.fixture_digest for f in self.fixtures)

    @property
    def hidden_digest(self) -> str:
        return _combined(f.hidden_digest for f in self.fixtures)


def _combined(digests: object) -> str:
    joined = "\n".join(digests)  # type: ignore[arg-type]
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()


def _task(document: dict[str, object]) -> TaskRequest:
    targets = document["targets"]
    constraints = document["constraints"]
    if not isinstance(targets, list) or not isinstance(constraints, list):
        raise FixtureError("task targets and constraints must be lists")
    return TaskRequest(
        str(document["objective"]),
        tuple(
            CodingTarget(
                RepositoryPath(str(item["path"])),
                FileChangeKind(str(item["operation"])),
            )
            for item in targets
        ),
        tuple(str(item) for item in constraints),
    )


def load_fixture_set(manifest: Path = MANIFEST) -> FixtureSet:
    """Load the manifest and verify every declared revision digest."""
    document = json.loads(manifest.read_text(encoding="utf-8"))
    base = manifest.parent
    fixtures: list[Fixture] = []
    for entry in document["fixtures"]:
        fixture_id = entry["id"]
        root = base / "fixtures" / fixture_id
        hidden = base / "hidden" / fixture_id
        task_document = json.loads((root / "task.json").read_text(encoding="utf-8"))
        fixture = Fixture(
            fixture_id,
            str(task_document["category"]),
            _task(task_document),
            root / "repository",
            hidden,
            root / "reference_proposal.json",
            _fixture_digest(root),
            tree_digest(hidden),
        )
        if fixture.fixture_digest != entry["fixture_digest"]:
            raise FixtureError(f"{fixture_id}: fixture changed without a new revision")
        if fixture.hidden_digest != entry["hidden_digest"]:
            raise FixtureError(
                f"{fixture_id}: hidden tests changed without a new revision"
            )
        if (fixture.template / HIDDEN_ROOT).exists():
            raise FixtureError(
                f"{fixture_id}: template must not contain {HIDDEN_ROOT}/"
            )
        fixtures.append(fixture)
    result = FixtureSet(
        str(document["fixture_set"]),
        str(document["revision"]),
        str(document["hidden_revision"]),
        tuple(fixtures),
    )
    if result.fixture_digest != document["fixture_set_digest"]:
        raise FixtureError("fixture set digest mismatch")
    if result.hidden_digest != document["hidden_set_digest"]:
        raise FixtureError("hidden-test set digest mismatch")
    return result


def _fixture_digest(root: Path) -> str:
    # Template and task only; the reference proposal is replay-mode material.
    return _combined(
        (tree_digest(root / "repository"), tree_digest_file(root / "task.json"))
    )


def tree_digest_file(path: Path) -> str:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _git_environment() -> dict[str, str]:
    environment = {
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_CONFIG_SYSTEM": os.devnull,
    }
    if os.name == "nt":
        environment["SystemRoot"] = os.environ["SystemRoot"]
    return environment


def provision(fixture: Fixture, target: Path, git: Path) -> Path:
    """Copy the template (never the hidden tests) and commit it; returns root."""
    shutil.copytree(
        fixture.template,
        target,
        ignore=shutil.ignore_patterns("__pycache__", ".*"),
    )
    for arguments in (
        ("init", "--initial-branch=main", "--template="),
        ("add", "--all"),
        (
            "-c",
            "user.name=ForgeAI evaluation",
            "-c",
            "user.email=evaluation@forgeai.invalid",
            "commit",
            "--quiet",
            "--no-gpg-sign",
            "-m",
            f"fixture {fixture.fixture_id}",
        ),
    ):
        subprocess.run(
            [str(git), *arguments],
            cwd=target,
            env=_git_environment(),
            check=True,
            capture_output=True,
            timeout=30,
            shell=False,
        )
    return target
