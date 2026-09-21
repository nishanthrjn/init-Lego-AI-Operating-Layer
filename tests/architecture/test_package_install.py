"""ADR-001/002 and F0: typing, inert imports and actual built-wheel isolation."""

import os
import subprocess
import sys
import tarfile
import venv
import zipfile
from pathlib import Path


def run(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args, cwd=cwd, capture_output=True, text=True, timeout=120, check=False
    )


def test_cross_kind_typing(tmp_path: Path) -> None:
    fixture = tmp_path / "identity_misuse.py"
    fixture.write_text(
        "from legoai.kernel.identity import TenantId, PrincipalId\n"
        "def tenant(value: TenantId) -> None: ...\n"
        "def principal(value: PrincipalId) -> None: ...\n"
        "tenant(TenantId('ok'))\nprincipal(PrincipalId('ok'))\n"
        "tenant(PrincipalId('wrong'))\nprincipal(TenantId('wrong'))\n",
        encoding="utf-8",
    )
    result = run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(fixture)],
        tmp_path,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 2, result.stdout
    assert all("[arg-type]" in error for error in errors)
    assert 'incompatible type "PrincipalId"; expected "TenantId"' in errors[0]
    assert 'incompatible type "TenantId"; expected "PrincipalId"' in errors[1]


def test_inert_import(tmp_path: Path) -> None:
    # Preload stdlib dependencies; then observe only our package import interval.
    script = """
import dataclasses, datetime, hashlib, json, logging, threading, socket, os, sys
from unittest.mock import patch
handlers = tuple(logging.getLogger().handlers)
threads = tuple(threading.enumerate())
def denied(*args, **kwargs):
    raise AssertionError("import side effect")
def audit(event, args):
    if event == "open":
        path, mode, flags = args
        if not isinstance(path, str) or not path.endswith((".py", ".pyc")):
            raise AssertionError("non-code file access")
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_TRUNC | os.O_APPEND):
            raise AssertionError("file write")
    if event.startswith(("socket.", "subprocess.", "sqlite3.")) or event in {"os.mkdir", "os.remove", "os.rename", "os.system"}:
        raise AssertionError(event)
sys.addaudithook(audit)
with patch.object(threading.Thread, "start", denied), patch.object(logging, "basicConfig", denied), patch.object(os, "getenv", denied), patch.object(type(os.environ), "__getitem__", denied):
    import legoai
    import legoai.kernel
    import legoai.kernel.identity
    import legoai.kernel.references
    import legoai.kernel.versions
    import legoai.kernel.context
    import legoai.kernel.errors
    import legoai.kernel.effects
    import legoai.governance
    import legoai.governance.values
    import legoai.application.values
    import legoai.reference.application.configuration
    import legoai.application.ports
    import legoai.evidence.values
    import legoai.reference.application.records
    import legoai.reference.application.migrations
assert tuple(logging.getLogger().handlers) == handlers
assert tuple(threading.enumerate()) == threads
assert {name for name in sys.modules if name.startswith("legoai.")} == {
    "legoai.kernel", "legoai.kernel.identity", "legoai.kernel.references",
    "legoai.kernel.versions", "legoai.kernel.context", "legoai.kernel.errors",
    "legoai.kernel.effects", "legoai.governance", "legoai.governance.values",
    "legoai.application", "legoai.application.values", "legoai.reference",
    "legoai.reference.application", "legoai.reference.application.configuration",
    "legoai.application.ports", "legoai.evidence", "legoai.evidence.values",
    "legoai.reference.application.records", "legoai.reference.application.migrations"
}
"""
    result = run([sys.executable, "-I", "-B", "-c", script], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert list(tmp_path.iterdir()) == []


def test_build_and_fresh_wheel(tmp_path: Path) -> None:
    root = Path(__file__).resolve().parents[2]
    artifacts = tmp_path / "artifacts"
    result = run(
        ["uv", "build", "--no-build-isolation", "--out-dir", str(artifacts)], root
    )
    assert result.returncode == 0, result.stdout + result.stderr
    wheels = list(artifacts.glob("*.whl"))
    archives = list(artifacts.glob("*.tar.gz"))
    assert len(wheels) == len(archives) == 1
    expected = {
        "legoai/__init__.py",
        "legoai/kernel/__init__.py",
        "legoai/kernel/identity.py",
        "legoai/kernel/references.py",
        "legoai/kernel/versions.py",
        "legoai/kernel/context.py",
        "legoai/kernel/errors.py",
        "legoai/kernel/effects.py",
        "legoai/governance/__init__.py",
        "legoai/governance/values.py",
        "legoai/py.typed",
        "legoai/application/__init__.py",
        "legoai/application/values.py",
        "legoai/reference/__init__.py",
        "legoai/reference/application/__init__.py",
        "legoai/reference/application/configuration.py",
        "legoai/reference/application/records.py",
        "legoai/reference/application/migrations.py",
        "legoai/application/ports.py",
        "legoai/evidence/__init__.py",
        "legoai/evidence/values.py",
    }
    with zipfile.ZipFile(wheels[0]) as wheel:
        names = set(wheel.namelist())
        assert {
            n for n in names if not n.split("/")[0].endswith(".dist-info")
        } == expected
        metadata = wheel.read(
            next(n for n in names if n.endswith("/METADATA"))
        ).decode()
        assert "Requires-Dist:" not in metadata
        assert "Requires-Python: <3.15,>=3.14" in metadata
    with tarfile.open(archives[0], "r:gz") as archive:
        names = {
            str(Path(n).relative_to(Path(n).parts[0])).replace("\\", "/")
            for n in archive.getnames()
        }
        assert {f"src/{n}" for n in expected} <= names
        assert all(
            not any(
                part in {".venv", "__pycache__", "planning", ".git"}
                for part in Path(n).parts
            )
            for n in names
        )
        assert names == {f"src/{n}" for n in expected} | {
            "pyproject.toml",
            "uv.lock",
            ".python-version",
            "PKG-INFO",
            ".gitignore",
            "docs/development.md",
            "tests/unit/kernel/test_identity.py",
            "tests/unit/kernel/test_foundation.py",
            "tests/unit/governance/test_context.py",
            "tests/unit/application/test_configuration.py",
            "tests/__init__.py",
            "tests/support/__init__.py",
            "tests/support/configuration_store.py",
            "tests/support/record_fixtures.py",
            "tests/unit/application/test_records.py",
            "tests/security/test_record_decoding.py",
            "tests/migration/test_application_records.py",
            "tests/contracts/conftest.py",
            "tests/contracts/test_configuration_store.py",
            "tests/architecture/test_import_boundaries.py",
            "tests/architecture/test_package_install.py",
        }
    environment = tmp_path / "installed"
    venv.EnvBuilder(with_pip=False).create(environment)
    interpreter = environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )
    result = run(
        [
            "uv",
            "pip",
            "install",
            "--python",
            str(interpreter),
            "--no-deps",
            "--offline",
            str(wheels[0]),
        ],
        tmp_path,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    script = """
import sys
from pathlib import Path
from importlib.metadata import version, requires
import legoai.kernel.identity as identity
import legoai.kernel.references as references
import legoai.kernel.context as context
import legoai.kernel.versions as versions
import legoai.kernel.errors as errors
import legoai.kernel.effects as effects
import legoai.governance.values as governance
import legoai.application.values as application
import legoai.reference.application.configuration as configuration
import legoai.application.ports as ports
import legoai.evidence.values as evidence
import legoai.reference.application.records as records
import legoai.reference.application.migrations as migrations
for module in (references, context, versions, errors, effects, governance, application, configuration, ports, evidence, records, migrations):
    assert Path(module.__file__).is_relative_to(Path(sys.prefix))
assert migrations.supported_migrations().transitions == ()
assert isinstance(records.decode_publication_result(b'{}'), records.RecordFailure)
target = references.ConfigurationRef(references.ApplicationRef(references.ReferenceScope("owner", identity.TenantId("t")), identity.ApplicationId("app")), "fixture")
result = configuration.compose_configuration(target, (), contract_version=versions.Version(0, 1, 0), interpretation_version=versions.Version(0, 1, 0))
assert result.effective.max_input_length == 4096
assert ports.HeadQuery(target).subject == target
assert evidence.RequirementRef(target.application.scope, "required", versions.Version(0, 1, 0)).scope == target.application.scope
assert versions.Version(0, 1, 0) < versions.Version(0, 2, 0)
assert context.TenantContext(identity.TenantId("t")).tenant_id == identity.TenantId("t")
assert governance.Principal(references.PrincipalRef("issuer", identity.PrincipalId("p"))).reference.principal_id == identity.PrincipalId("p")
assert len(effects.EffectExtent) == 4
assert len(errors.ErrorCategory) == 5
assert Path(identity.__file__).is_relative_to(Path(sys.prefix))
assert identity.TenantId("abc").value == "abc"
assert identity.PrincipalId("abc").value == "abc"
assert version("legoai-reference") == "0.1.0.dev0"
assert not requires("legoai-reference")
assert Path(identity.__file__).parents[1].joinpath("py.typed").is_file()
"""
    result = run([str(interpreter), "-I", "-B", "-c", script], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr


def test_f1_static_misuse(tmp_path: Path) -> None:
    fixture = tmp_path / "f1_misuse.py"
    fixture.write_text(
        "from legoai.kernel.identity import ApplicationId, TenantId, OperationId, PrincipalId, RequestId, CorrelationId, TraceId\n"
        "from legoai.kernel.references import OwnerRevision\n"
        "from legoai.kernel.context import TenantContext\n"
        "from legoai.governance.values import Principal\n"
        "def tenant(value: TenantId) -> None: ...\n"
        "def operation(value: OperationId) -> None: ...\n"
        "def principal(value: Principal) -> None: ...\n"
        "def request(value: RequestId) -> None: ...\n"
        "def correlation(value: CorrelationId) -> None: ...\n"
        "def misuse(revision: OwnerRevision) -> None:\n"
        "    operation(revision)\n"
        "tenant(ApplicationId('a'))\n"
        "principal(PrincipalId('p'))\n"
        "tenant(TenantContext(TenantId('t')))\n"
        "request(OperationId('o'))\n"
        "correlation(TraceId('t'))\n",
        encoding="utf-8",
    )
    result = run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(fixture)],
        tmp_path,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    expected = (
        ("OwnerRevision", "OperationId"),
        ("ApplicationId", "TenantId"),
        ("PrincipalId", "Principal"),
        ("TenantContext", "TenantId"),
        ("OperationId", "RequestId"),
        ("TraceId", "CorrelationId"),
    )
    assert len(errors) == len(expected), result.stdout
    for error, (actual, required) in zip(errors, expected, strict=True):
        assert "[arg-type]" in error
        assert f'incompatible type "{actual}"; expected "{required}"' in error


def test_f2_static_misuse(tmp_path: Path) -> None:
    fixture = tmp_path / "f2_misuse.py"
    fixture.write_text(
        "from legoai.application.values import SourceProvenance, SourceLayer, CapturedCandidate\n"
        "from legoai.kernel.versions import Version\n"
        "from legoai.kernel.references import ConfigurationRef\n"
        "from legoai.reference.application.configuration import capture_candidate, compose_configuration\n"
        "def misuse(target: ConfigurationRef, source: SourceProvenance, candidate: CapturedCandidate) -> None:\n"
        "    capture_candidate({}, target=target, provenance=source, layer='base')\n"
        "    capture_candidate({}, target=Version(0, 1, 0), provenance=source, layer=SourceLayer.BASE)\n"
        "    compose_configuration(target, [candidate], contract_version=Version(0, 1, 0), interpretation_version=Version(0, 1, 0))\n",
        encoding="utf-8",
    )
    result = run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(fixture)],
        tmp_path,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 3, result.stdout
    for error, expected in zip(
        errors,
        ("SourceLayer", "ConfigurationRef", "tuple[CapturedCandidate, ...]"),
        strict=True,
    ):
        assert "[arg-type]" in error and f'expected "{expected}"' in error


def test_f4_static_misuse(tmp_path: Path) -> None:
    fixture = tmp_path / "f4_misuse.py"
    fixture.write_text(
        "from legoai.application.ports import ConfigurationHead, DutyRef, HeadQuery\n"
        "from legoai.kernel.references import ConfigurationRef, ConfigurationRevisionRef\n"
        "from legoai.kernel.identity import TenantId\n"
        "from legoai.evidence.values import RequirementRef\n"
        "def misuse(subject: ConfigurationRef, revision: ConfigurationRevisionRef, requirement: RequirementRef) -> None:\n"
        "    ConfigurationHead(revision, revision)\n"
        "    DutyRef(subject, requirement)\n"
        "    HeadQuery(TenantId('tenant'))\n",
        encoding="utf-8",
    )
    result = run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(fixture)],
        tmp_path,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 3, result.stdout
    for error, expected in zip(
        errors, ("OwnerRevision", "ObligationId", "ConfigurationRef"), strict=True
    ):
        assert "[arg-type]" in error and f'expected "{expected}"' in error


def test_f5_static_misuse(tmp_path: Path) -> None:
    fixture = tmp_path / "f5_misuse.py"
    fixture.write_text(
        "from legoai.reference.application.records import encode_published_configuration\n"
        "from legoai.reference.application.migrations import MigrationObservation\n"
        "from legoai.kernel.references import OwnerRevision\n"
        "def misuse(revision: OwnerRevision) -> None:\n"
        "    encode_published_configuration({})\n"
        "    MigrationObservation(revision, 1, True, None)\n",
        encoding="utf-8",
    )
    result = run(
        [sys.executable, "-m", "mypy", "--strict", "--no-incremental", str(fixture)],
        tmp_path,
    )
    assert result.returncode == 1, result.stdout + result.stderr
    errors = [line for line in result.stdout.splitlines() if ": error:" in line]
    assert len(errors) == 2, result.stdout
    for error, expected in zip(errors, ("PublishedConfiguration", "int"), strict=True):
        assert "[arg-type]" in error and f'expected "{expected}"' in error
