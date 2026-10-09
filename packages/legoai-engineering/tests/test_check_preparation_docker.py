"""Explicit qualification: ONE public wheel acquisition, then offline checks.

Set LEGOAI_QUALIFY_PROJECT_CHECKS=1 through the focused validator. No live model.
"""

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from legoai_engineering.checks.preparation import (
    inspect_check_project,
    prepare_check_environment,
)
from legoai_engineering.checks.sandboxed import (
    CheckInputPolicy,
    SandboxedEngineeringChecks,
)
from legoai_engineering.checks.values import (
    CheckKind,
    CheckOutcome,
    CheckPolicy,
    CheckRequest,
)
from legoai_engineering.repository.local import (
    LocalRepositoryWorkspace,
    LocalWorkspaceRoot,
)
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.sandbox.docker import (
    DockerSandbox,
    DockerSandboxConfig,
    SandboxImage,
)
from legoai_engineering.sandbox.prepared import PreparationError, PreparationFailure
from legoai_engineering.sandbox.values import SandboxPolicy, SandboxRequest


@pytest.mark.skipif(
    os.environ.get("LEGOAI_QUALIFY_PROJECT_CHECKS") != "1",
    reason="explicit dependency-acquisition qualification only",
)
def test_real_dependency_preparation_and_offline_checks() -> None:
    root = (
        Path(__file__).resolve().parents[3] / "examples/forgeai/fixtures/project_checks"
    )
    docker, uv = shutil.which("docker"), shutil.which("uv")
    assert docker and uv
    workspace = LocalRepositoryWorkspace(
        LocalWorkspaceRoot(root),
        WorkspacePolicy(262144, 65536, 4096, 32, (".git", ".venv")),
    )
    metadata = inspect_check_project(workspace)
    base = DockerSandbox(
        DockerSandboxConfig(Path(docker), SandboxImage.PYTHON_CHECKS),
        SandboxPolicy(timeout_seconds=180, max_output_bytes=1048576),
    )
    inputs = CheckInputPolicy(
        (RepositoryPath("src"), RepositoryPath("tests")),
        (RepositoryPath("pyproject.toml"),),
    )
    plan = (
        CheckRequest(
            CheckKind.RUFF_CHECK, (RepositoryPath("src"), RepositoryPath("tests"))
        ),
        CheckRequest(CheckKind.MYPY, (RepositoryPath("src"),)),
        CheckRequest(CheckKind.PYTEST, (RepositoryPath("tests"),)),
    )
    generic = SandboxedEngineeringChecks(workspace, base, inputs, CheckPolicy(120))
    missing = base.execute(
        SandboxRequest("import importlib.util; print(importlib.util.find_spec('idna'))")
    )
    assert missing.stdout.strip() == b"None"
    assert generic.check(plan[-1]).outcome is not CheckOutcome.PASSED
    with pytest.raises(PreparationError) as incompatible:
        prepare_check_environment(
            replace(metadata, python_requirement=">=4"), Path(docker), Path(uv)
        )
    assert incompatible.value.reason is PreparationFailure.PYTHON_INCOMPATIBLE
    environment = prepare_check_environment(metadata, Path(docker), Path(uv))
    assert environment.base_image == base.config.image
    prepared = DockerSandbox(
        DockerSandboxConfig(Path(docker), environment), base.policy
    )
    checks = SandboxedEngineeringChecks(workspace, prepared, inputs, CheckPolicy(120))
    for request in plan:
        result = checks.check(request)
        assert result.outcome is CheckOutcome.PASSED, (
            request.kind,
            result.stdout,
            result.stderr,
        )
    probe = prepared.execute(
        SandboxRequest("""
import hashlib, importlib.metadata, json, pathlib, socket
tools = {name: hashlib.sha256(pathlib.Path('/usr/local/bin/' + name).read_bytes()).hexdigest()
         for name in ('ruff', 'mypy', 'pytest')}
print(json.dumps({'tools': tools, 'interfaces': socket.if_nameindex(),
                  'versions': {n: importlib.metadata.version(n) for n in tools}}))
""")
    )
    data = json.loads(probe.stdout)
    assert data["interfaces"] == [[1, "lo"]]
    assert data["versions"] == {"ruff": "0.16.8", "mypy": "2.3.1", "pytest": "9.1.1"}
    baseline = base.execute(
        SandboxRequest("""
import hashlib, json, pathlib
print(json.dumps({name: hashlib.sha256(pathlib.Path('/usr/local/bin/' + name).read_bytes()).hexdigest()
                  for name in ('ruff', 'mypy', 'pytest')}))
""")
    )
    assert data["tools"] == json.loads(baseline.stdout)
    print("qualified prepared image: " + environment.image)
