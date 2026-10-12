"""ADR-014: public/private boundary of the local governed host.

`legoai.runtime.api` is contract-only; `legoai.runtime.local` is the single
public module allowed to import reference realizations or private composition.
Migrated consumers, including generative-media composition, import neither.
"""

import ast
import inspect
import os
import typing
from collections.abc import Iterator
from pathlib import Path

import pytest

import legoai.runtime.api as api
import legoai.runtime.local as local
from legoai.reference.model import (
    ollama_chat_capability_id,
    ollama_embedding_capability_id,
)
from tests.architecture.test_import_boundaries import violations

ROOT = Path(__file__).resolve().parents[2]
INTERNAL = ("legoai.reference", "legoai.runtime._composition")
# Existing authorization-adversarial fixtures, not application/domain code.
# Keep this exception exact; no production consumer may join it.
INTERNAL_TEST_FIXTURES = {
    "examples/forgeai/evaluation/tests/test_content_discovery_1.py",
    # Synthetic S1 bootstrap for local TLS tests; production uses public APIs.
    "examples/forgeai/tests/test_remote_profile.py",
    "examples/forgeai/tests/test_provider.py",  # synthetic Secret/TLS fixture only
}
# Never opened: excluded by path before any file is read.
EXCLUDED_PARTS = {".venv", "node_modules", "__pycache__", "assessment_starter"}


def _imports(source: str) -> set[str]:
    targets: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            targets.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            targets.add(node.module)
    return targets


def _internal(targets: set[str]) -> set[str]:
    return {
        t for t in targets if any(t == p or t.startswith(p + ".") for p in INTERNAL)
    }


@pytest.mark.parametrize(
    "source",
    [
        "from legoai.reference.catalog import InMemoryCatalog",
        "from legoai.runtime._composition.agent import GovernedAgentChat",
        "from legoai.runtime.local import open_local_host",
        "import legoai.reference.execution",
    ],
)
def test_runtime_api_is_contract_only(source: str) -> None:
    assert "runtime-api" in violations({"legoai.runtime.api": source})


def test_runtime_api_may_use_owner_contracts() -> None:
    for source in (
        "from legoai.execution.agent.ports import AgentRuntimePort",
        "from legoai.governance.ports import AuthorizationPort",
        "from legoai.intelligence.model.ports import ModelPort",
        "from legoai.kernel.references import ConfigurationRef",
    ):
        assert "runtime-api" not in violations({"legoai.runtime.api": source})


def test_only_runtime_local_publicly_imports_internals() -> None:
    src = ROOT / "src"
    importers = set()
    for path in src.rglob("*.py"):
        module = ".".join(path.relative_to(src).with_suffix("").parts)
        if module.startswith(INTERNAL):
            continue
        if _internal(_imports(path.read_text(encoding="utf-8"))):
            importers.add(module)
    assert importers == {"legoai.runtime.local"}


def _types(annotation: object) -> Iterator[object]:
    yield annotation
    for argument in typing.get_args(annotation):
        yield from _types(argument)


def _public_callables() -> Iterator[tuple[str, object]]:
    for module in (api, local):
        for name, value in vars(module).items():
            if (
                name.startswith("_")
                or getattr(value, "__module__", None) != module.__name__
            ):
                continue
            if inspect.isclass(value):
                for member_name, member in vars(value).items():
                    if not member_name.startswith("_") and callable(member):
                        yield f"{name}.{member_name}", member
                    if isinstance(member, property) and member.fget is not None:
                        yield f"{name}.{member_name}", member.fget
            yield name, value


def test_public_signatures_expose_no_internal_types() -> None:
    checked = 0
    for name, value in _public_callables():
        target = vars(value).get("__init__") if inspect.isclass(value) else value
        if target is None:
            continue
        try:
            hints = typing.get_type_hints(target)
        except TypeError:
            continue
        for annotation in hints.values():
            for item in _types(annotation):
                module = getattr(item, "__module__", "")
                assert not str(module).startswith(INTERNAL), (name, item)
                checked += 1
    assert checked > 50


def test_host_members_accept_no_authority_or_code() -> None:
    forbidden = {
        "Grant",
        "Principal",
        "SecurityContext",
        "TenantContext",
        "PrincipalRef",
        "PolicyRef",
        "PluginDeclaration",
        "ConfigurationRevisionRef",
        "Callable",
    }
    for name, member in vars(api.GovernedHost).items():
        if name.startswith("_") or not callable(member):
            continue
        hints = typing.get_type_hints(member)
        hints.pop("return", None)
        for annotation in hints.values():
            names = {
                getattr(item, "__name__", str(item)) for item in _types(annotation)
            }
            assert not names & forbidden, (name, names)


def test_model_purposes_are_closed_and_match_existing_capabilities() -> None:
    assert [p.value for p in api.ModelPurpose] == ["chat", "embedding"]
    assert api.ModelPurpose.CHAT.capability_id == ollama_chat_capability_id()
    assert api.ModelPurpose.EMBEDDING.capability_id == ollama_embedding_capability_id()


def test_host_failure_vocabulary_is_closed() -> None:
    assert {f.value for f in api.HostFailure} == {
        "invalid_configuration",
        "stale_configuration",
        "unknown_binding",
        "contribution_conflict",
        "unavailable_provider",
        "incompatible_provider",
        "invalid_grant",
        "unsupported_composition",
        "missing_dependency",
        "initialization_failure",
        "grant_not_configured",
        "subject_out_of_scope",
        "purpose_unavailable",
        "foreign_context",
        "capacity_exhausted",
        "wrong_event_loop",
        "closed",
        "duplicate_claim",
        "wrong_execution_state",
        "unauthorized",
        "deadline_exceeded",
    }


def test_remote_http_status_stays_private_and_out_of_public_contracts() -> None:
    for relative in (
        "src/legoai/runtime/api.py",
        "src/legoai/intelligence/model/ports.py",
        "src/legoai/intelligence/model/values.py",
        "src/legoai/execution/agent/ports.py",
        "src/legoai/kernel/errors.py",
    ):
        source = (ROOT / relative).read_text(encoding="utf-8")
        assert "provider_status" not in source
        assert "_remote_chat_http_status" not in source
    source = (ROOT / "src/legoai/runtime/_composition/remote_model.py").read_text(
        encoding="utf-8"
    )
    assert not any(
        name in source.lower() for name in ("huggingface", "nscale", "kisski")
    )


def test_local_host_has_no_generic_lookup_or_dynamic_loading() -> None:
    tree = ast.parse((ROOT / "src/legoai/runtime/local.py").read_text(encoding="utf-8"))
    forbidden = {
        "ProviderRegistry",
        "ServiceLocator",
        "ImplementationRegistry",
        "eval",
        "exec",
        "compile",
        "__import__",
        "import_module",
        "getattr",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            assert node.name not in forbidden
        if isinstance(node, ast.Name):
            assert node.id not in forbidden, node.id
        if isinstance(node, ast.Attribute):
            assert node.attr not in forbidden, node.attr


def _walk(root: Path) -> Iterator[Path]:
    # Prune before descending: excluded trees are never listed or read.
    for directory, subdirectories, files in os.walk(root):
        subdirectories[:] = sorted(d for d in subdirectories if d not in EXCLUDED_PARTS)
        yield from (Path(directory) / f for f in sorted(files) if f.endswith(".py"))


def _consumer_files() -> Iterator[Path]:
    # Core's own top-level examples demonstrate internals; only the public-host
    # example among them is a consumer.
    yield ROOT / "examples" / "local_host.py"
    for child in sorted((ROOT / "examples").iterdir()):
        if child.is_dir() and child.name not in EXCLUDED_PARTS:
            yield from _walk(child)
    for kind in ("src", "examples"):
        for root in sorted((ROOT / "packages").glob(f"*/{kind}")):
            yield from _walk(root)


def test_consumers_import_no_core_internals_except_owner_fixtures() -> None:
    if not (ROOT / "packages").is_dir():
        pytest.skip("repository consumer layout unavailable (e.g. extracted sdist)")
    offenders = set()
    for path in _consumer_files():
        if _internal(_imports(path.read_text(encoding="utf-8"))):
            offenders.add(path.relative_to(ROOT).as_posix())
    assert offenders == INTERNAL_TEST_FIXTURES


def test_migrated_consumers_do_not_self_issue_authority() -> None:
    if not (ROOT / "packages").is_dir():
        pytest.skip("repository consumer layout unavailable (e.g. extracted sdist)")
    migrated = [
        *sorted((ROOT / "examples/documind/src").rglob("*.py")),
        *sorted((ROOT / "packages/legoai-engineering/examples").glob("*.py")),
        ROOT / "examples/local_host.py",
    ]
    for path in migrated:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                called = node.func
                name = (
                    called.id
                    if isinstance(called, ast.Name)
                    else getattr(called, "attr", "")
                )
                assert name not in {"Grant", "SecurityContext"}, (path, name)
