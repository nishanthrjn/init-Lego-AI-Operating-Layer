"""Operator-run clean wheel consumer proof, outside checkout; no model calls."""

import subprocess
import sys
import venv
from pathlib import Path


def test_structure_installed_public_consumer(tmp_path: Path) -> None:
    package = Path(__file__).resolve().parents[1]
    repository = package.parents[1]
    artifacts = tmp_path / "wheels"

    def run(command: list[str], cwd: Path = tmp_path) -> None:
        result = subprocess.run(
            command, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
        )
        assert result.returncode == 0, result.stdout + result.stderr

    for project in (package, repository):
        run(
            [
                "uv",
                "build",
                "--wheel",
                "--no-build-isolation",
                "--out-dir",
                str(artifacts),
            ],
            project,
        )
    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=False).create(environment)
    python = str(
        environment
        / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    )
    engineering = next(artifacts.glob("legoai_engineering-*.whl"))
    core = next(artifacts.glob("legoai_reference-*.whl"))
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            python,
            "--offline",
            "--no-deps",
            str(engineering),
        ]
    )
    run(
        [
            python,
            "-I",
            "-B",
            "-c",
            """
import sys
from legoai_engineering.repository.structure import RepositoryStructurePolicy, RepositoryStructure
from legoai_engineering.repository.workspace import RepositoryPath, WorkspaceEntry, WorkspaceEntryKind
p = RepositoryStructurePolicy((RepositoryPath('src'),))
s = RepositoryStructure(p, (WorkspaceEntry(p.roots[0], WorkspaceEntryKind.DIRECTORY),))
assert s.model_bytes() and len(s.digest()) == 64
assert 'legoai' not in sys.modules
""",
        ]
    )
    run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            python,
            "--offline",
            "--no-deps",
            str(core),
        ]
    )
    run(
        [
            python,
            "-I",
            "-B",
            "-c",
            """
from pathlib import Path
from datetime import UTC, datetime, timedelta
import sys
from legoai.governance.values import GrantId, PolicyRef
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import ApplicationRef, ConfigurationRef, ConfigurationRevisionRef, PrincipalRef, ReferenceScope
from legoai.kernel.versions import Version
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import ProviderId
from legoai.runtime.api import LocalHostConfig, OperatorGrant, ModelBindingConfig, OllamaSettings
from legoai.runtime.local import open_local_host
from legoai_engineering.repository.structure import RepositoryStructurePolicy
from legoai_engineering.repository.structure_authorized import AuthorizedRepositoryStructure, REPOSITORY_STRUCTURE_ACTION
from legoai_engineering.repository.workspace import RepositoryPath, WorkspacePolicy
from legoai_engineering.repository.local import LocalRepositoryWorkspace, LocalWorkspaceRoot
def audit(event, args):
    if event.startswith('socket.'):
        raise AssertionError('network forbidden')
sys.addaudithook(audit)
now = datetime(2026, 10, 4, tzinfo=UTC)
reference = ConfigurationRef(ApplicationRef(ReferenceScope('operator', TenantId('local')), ApplicationId('structure')), 'workspace')
config = LocalHostConfig(
    ConfigurationRevisionRef(reference, 'r1', Version(1,0,0)),
    PrincipalRef('operator', PrincipalId('operator')),
    PolicyRef('operator', 'local', Version(1,0,0)),
    (OperatorGrant(GrantId('structure'), REPOSITORY_STRUCTURE_ACTION, 'workspace', now, now+timedelta(hours=1)),),
    (ModelBindingConfig('unused', ModelRequirement('unused'), OllamaSettings('http://localhost:11434', 'unused', 'unused', 1.0, ProviderId('local'))),),
    max_executions=8,
)
host = open_local_host(config, {'revision':'r1', 'binding':'unused'}, clock=lambda: now)
root = Path.cwd() / 'repository'
(root / 'src').mkdir(parents=True)
(root / 'src' / 'a.py').write_text('not read')
context = host.security_context(reference, REPOSITORY_STRUCTURE_ACTION, 'workspace')
reader = AuthorizedRepositoryStructure(reference,
    LocalRepositoryWorkspace(LocalWorkspaceRoot(root), WorkspacePolicy(1,1,512,6,())),
    context, host.authorization, RepositoryStructurePolicy((RepositoryPath('src'),)), lambda: now)
result = reader.acquire(context.tenant_context)
assert [e.path.value for e in result.entries] == ['src','src/a.py']
assert 'not read' not in result.model_bytes().decode()
""",
        ]
    )
