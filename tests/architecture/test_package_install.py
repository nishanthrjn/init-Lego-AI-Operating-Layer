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
import dataclasses, logging, threading, socket, os, sys
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
    import legoai.kernel.provenance
    import legoai.governance
    import legoai.governance.values
    import legoai.evidence
    import legoai.evidence.values
    import legoai.application.values
    import legoai.application.ports
    import legoai.reference.application.configuration
    import legoai.reference.application.codec
    import legoai.reference.application.sqlite_store
    import legoai.reference.application.recovery
    import legoai.observability
    import legoai.observability.values
    import legoai.observability.ports
    import legoai.reference.observation
    import legoai.plugins
    import legoai.plugins.values
    import legoai.capabilities
    import legoai.capabilities.values
    import legoai.reference.declarations
    import legoai.reference.resolution
    import legoai.reference.deterministic
    import legoai.runtime
    import legoai.runtime._composition
    import legoai.runtime._composition.direct
    import legoai.intelligence.model.ports
    import legoai.intelligence.model.routing
    import legoai.reference.model_routing
    import legoai.reference.model_fake
    import legoai.execution.agent.values
    import legoai.execution.agent.ports
    import legoai.reference.agent
    tenant = legoai.kernel.context.TenantContext(legoai.kernel.identity.TenantId("t"))
    target = legoai.kernel.references.ConfigurationRef(
        legoai.kernel.references.ApplicationRef(
            legoai.kernel.references.ReferenceScope("operator", tenant.tenant_id),
            legoai.kernel.identity.ApplicationId("app")), "models")
    revision = legoai.kernel.references.ConfigurationRevisionRef(
        target, "r1", legoai.kernel.versions.Version(1, 0, 0))
    requirement = legoai.intelligence.model.routing.ModelRequirement("reasoning")
    binding = legoai.intelligence.model.routing.ModelBinding(
        "binding", requirement, legoai.intelligence.model.values.ModelId("model"),
        legoai.intelligence.model.values.ProviderId("provider"))
    router = legoai.reference.model_routing.DeterministicModelRouter(revision, (binding,))
    assert router.route(requirement, tenant).selected == binding
assert tuple(logging.getLogger().handlers) == handlers
assert tuple(threading.enumerate()) == threads
assert {name for name in sys.modules if name.startswith("legoai.")} == {
    "legoai.kernel", "legoai.kernel.identity", "legoai.kernel.references",
    "legoai.kernel.versions", "legoai.kernel.context", "legoai.kernel.errors",
    "legoai.kernel.effects", "legoai.kernel.provenance",
    "legoai.governance", "legoai.governance.values",
    "legoai.evidence", "legoai.evidence.values",
    "legoai.application", "legoai.application.values", "legoai.application.ports",
    "legoai.reference",
    "legoai.reference.application", "legoai.reference.application.configuration",
    "legoai.reference.application.codec",
    "legoai.reference.application.sqlite_store",
    "legoai.reference.application.recovery",
    "legoai.observability", "legoai.observability.values", "legoai.observability.ports",
    "legoai.reference.observation",
    "legoai.plugins", "legoai.plugins.values", "legoai.plugins.ports",
    "legoai.capabilities", "legoai.capabilities.values", "legoai.capabilities.ports",
    "legoai.reference.declarations", "legoai.reference.resolution",
    "legoai.reference.deterministic",
    "legoai.runtime", "legoai.runtime._composition", "legoai.runtime._composition.direct",
    "legoai.intelligence", "legoai.intelligence.model",
    "legoai.intelligence.model.values", "legoai.intelligence.model.ports",
    "legoai.intelligence.model.routing", "legoai.reference.model_routing",
    "legoai.reference.model_fake",
    "legoai.execution", "legoai.execution.values", "legoai.execution.agent",
    "legoai.execution.agent.values", "legoai.execution.agent.ports",
    "legoai.reference.agent"
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
        "legoai/kernel/provenance.py",
        "legoai/governance/__init__.py",
        "legoai/governance/values.py",
        "legoai/evidence/__init__.py",
        "legoai/evidence/values.py",
        "legoai/py.typed",
        "legoai/application/__init__.py",
        "legoai/application/values.py",
        "legoai/application/ports.py",
        "legoai/reference/__init__.py",
        "legoai/reference/application/__init__.py",
        "legoai/reference/application/configuration.py",
        "legoai/reference/application/codec.py",
        "legoai/reference/application/sqlite_store.py",
        "legoai/reference/application/recovery.py",
        "legoai/observability/__init__.py",
        "legoai/observability/values.py",
        "legoai/observability/ports.py",
        "legoai/reference/observation.py",
        "legoai/plugins/__init__.py",
        "legoai/plugins/values.py",
        "legoai/capabilities/__init__.py",
        "legoai/capabilities/values.py",
        "legoai/reference/declarations.py",
        "legoai/reference/resolution.py",
        "legoai/reference/deterministic.py",
        "legoai/runtime/__init__.py",
        "legoai/runtime/_composition/__init__.py",
        "legoai/runtime/_composition/direct.py",
        "legoai/execution/__init__.py",
        "legoai/execution/values.py",
        "legoai/resources/__init__.py",
        "legoai/resources/values.py",
        "legoai/governance/ports.py",
        "legoai/reference/governance.py",
        "legoai/plugins/ports.py",
        "legoai/reference/plugins.py",
        "legoai/capabilities/ports.py",
        "legoai/reference/catalog.py",
        "legoai/evidence/ports.py",
        "legoai/reference/evidence.py",
        "legoai/execution/ports.py",
        "legoai/reference/execution.py",
        "legoai/runtime/_composition/governed.py",
        "legoai/intelligence/__init__.py",
        "legoai/intelligence/model/__init__.py",
        "legoai/intelligence/model/values.py",
        "legoai/intelligence/model/ports.py",
        "legoai/intelligence/model/routing.py",
        "legoai/reference/model_routing.py",
        "legoai/reference/model.py",
        "legoai/reference/model_fake.py",
        "legoai/runtime/_composition/model_governed.py",
        "legoai/execution/agent/__init__.py",
        "legoai/execution/agent/values.py",
        "legoai/execution/agent/ports.py",
        "legoai/reference/agent.py",
        "legoai/runtime/_composition/agent.py",
        "legoai/runtime/_composition/model_selection.py",
        "legoai/runtime/api.py",
        "legoai/runtime/local.py",
        # Qualified Secret, custody, disclosure, discovery and REMOTE modules.
        "legoai/evidence/custody.py",
        "legoai/governance/disclosure.py",
        "legoai/governance/provider_control.py",
        "legoai/governance/secret.py",
        "legoai/reference/_credential_https.py",
        "legoai/reference/_custody_codec.py",
        "legoai/reference/_custody_sqlite.py",
        "legoai/reference/_durable_evidence.py",
        "legoai/reference/_remote_attempts.py",
        "legoai/reference/_secret_domain.py",
        "legoai/reference/_secret_ledger.py",
        "legoai/reference/model_capabilities.py",
        "legoai/reference/model_openai_compatible.py",
        "legoai/reference/secret.py",
        "legoai/runtime/_composition/credential_https.py",
        "legoai/runtime/_composition/disclosure.py",
        "legoai/runtime/_composition/provider_discovery.py",
        "legoai/runtime/_composition/remote_attempt.py",
        "legoai/runtime/_composition/remote_model.py",
        "legoai/runtime/_composition/secret.py",
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
            "LICENSE",
            "docs/development.md",
            "docs/model-routing.md",
            "examples/model_routing.py",
            "docs/agent.md",
            "docs/ports-and-adapters.md",
            "examples/model_port.py",
            "tests/unit/reference/test_model_foundation.py",
            "examples/agent.py",
            "tests/unit/execution/test_agent.py",
            "tests/integration/composition/test_agent.py",
            "tests/architecture/test_agent.py",
            "tests/unit/kernel/test_identity.py",
            "tests/unit/kernel/test_foundation.py",
            "tests/unit/kernel/test_provenance.py",
            "tests/unit/governance/test_context.py",
            "tests/unit/application/test_configuration.py",
            "tests/unit/application/test_operation_result.py",
            "tests/unit/application/test_codec.py",
            "tests/unit/application/test_sqlite_store.py",
            "tests/unit/application/test_recovery.py",
            "tests/unit/evidence/test_values.py",
            "tests/unit/observability/test_values.py",
            "tests/unit/observability/test_sink.py",
            "tests/unit/capabilities/test_values.py",
            "tests/unit/plugins/test_values.py",
            "tests/unit/reference/test_declarations.py",
            "tests/unit/reference/test_resolution.py",
            "tests/unit/reference/test_deterministic.py",
            "tests/integration/composition/test_direct.py",
            "tests/integration/composition/test_import_inertness.py",
            "tests/__init__.py",
            "tests/contract/test_configuration_store.py",
            "tests/support/__init__.py",
            "tests/support/configuration_store.py",
            "tests/support/observation.py",
            "tests/support/migration_fixture.py",
            "tests/integration/application/test_migration_interruption.py",
            "tests/unit/execution/test_values.py",
            "tests/unit/governance/test_authority.py",
            "tests/unit/resources/test_values.py",
            "tests/unit/governance/test_ports.py",
            "tests/contract/test_authorization.py",
            "tests/support/governance.py",
            "tests/unit/plugins/test_ports.py",
            "tests/unit/reference/test_plugins.py",
            "tests/unit/capabilities/test_ports.py",
            "tests/contract/test_catalog.py",
            "tests/unit/reference/test_capability_resolution.py",
            "tests/unit/evidence/test_ports.py",
            "tests/unit/reference/test_evidence.py",
            "tests/unit/execution/test_ports.py",
            "tests/unit/reference/test_execution.py",
            "tests/unit/reference/test_coordinator.py",
            "tests/support/execution.py",
            "tests/integration/composition/test_governed_direct.py",
            "tests/unit/intelligence/test_model_values.py",
            "tests/unit/reference/test_model.py",
            "tests/unit/reference/test_model_routing.py",
            "tests/unit/reference/test_governance_registries.py",
            "tests/unit/reference/test_static_security_context_registry.py",
            "tests/integration/composition/test_model_governed.py",
            "tests/integration/composition/test_model_selection.py",
            "tests/architecture/test_import_boundaries.py",
            "tests/architecture/test_package_install.py",
            "tests/architecture/test_model_routing.py",
            "examples/local_host.py",
            "tests/integration/composition/test_local_host.py",
            "tests/architecture/test_local_host.py",
            "tests/architecture/test_credential_https.py",
            "tests/architecture/test_openai_compatible_remote.py",
            "tests/architecture/test_openai_compatible.py",
            "tests/architecture/test_provider_discovery.py",
            "tests/architecture/test_remote_attempts.py",
            "tests/architecture/test_remote_disclosure.py",
            "tests/architecture/test_secret_durable_custody.py",
            "tests/architecture/test_secret_ref.py",
            "tests/architecture/test_secret_source_s1.py",
            "tests/architecture/test_structured_output_live_probe_custody.py",
            "tests/architecture/test_structured_output.py",
            "tests/integration/composition/test_credential_https_exchange.py",
            "tests/integration/composition/test_openai_compatible_remote.py",
            "tests/integration/composition/test_openai_compatible.py",
            "tests/integration/composition/test_provider_discovery.py",
            "tests/integration/composition/test_provider_discovery_v2.py",
            "tests/integration/composition/test_remote_attempt_custody.py",
            "tests/integration/composition/test_remote_disclosure_gate.py",
            "tests/integration/composition/test_remote_disclosure.py",
            "tests/integration/composition/test_secret_uses.py",
            "tests/integration/composition/test_structured_output_routing.py",
            "tests/support/custody_scenario.py",
            "tests/support/openai_http.py",
            "tests/support/provider_discovery.py",
            "tests/support/remote_attempt_scenario.py",
            "tests/support/secret_ref_scenario.py",
            "tests/support/tls_server.py",
            "tests/support/tls/localhost.pem",
            "tests/support/tls/test-ca.pem",
            "tests/support/tls/untrusted.pem",
            "tests/support/tls/wrong-host.pem",
            "tests/unit/governance/test_disclosure.py",
            "tests/unit/governance/test_provider_control.py",
            "tests/unit/intelligence/test_structured_output.py",
            "tests/unit/reference/test_credential_https.py",
            "tests/unit/reference/test_model_list.py",
            "tests/unit/reference/test_model_structured_output.py",
            "tests/unit/reference/test_openai_compatible_exchange.py",
            "tests/unit/reference/test_openai_compatible.py",
            "tests/unit/reference/test_model_provider_diagnostics.py",
            "tests/unit/reference/test_remote_attempts.py",
            "tests/unit/reference/test_secret_durable_custody.py",
            "tests/unit/reference/test_secret_ref.py",
            "tests/unit/reference/test_secret_source_s1.py",
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
from datetime import datetime, timezone
from pathlib import Path
from importlib.metadata import version, requires
import asyncio
from legoai.reference.model_fake import FixedModel
from legoai.intelligence.model.values import ChatResult, ChatRequest, ChatMessage, ChatRole, ModelId, ProviderId
fixture = ChatResult("installed", ModelId("fixture"), ProviderId("offline"), None)
assert asyncio.run(FixedModel(fixture).chat(ChatRequest((ChatMessage(ChatRole.USER, "test"),)))) == fixture
import legoai.kernel.identity as identity
import legoai.kernel.references as references
import legoai.kernel.context as context
import legoai.kernel.versions as versions
import legoai.kernel.errors as errors
import legoai.kernel.effects as effects
import legoai.kernel.provenance as provenance
import legoai.governance.values as governance
import legoai.evidence.values as evidence
import legoai.application.values as application
import legoai.application.ports as ports
import legoai.reference.application.configuration as configuration
import legoai.reference.application.codec as codec
import legoai.reference.application.sqlite_store as sqlite_store
import legoai.reference.application.recovery as recovery
import legoai.observability.values as observability_values
import legoai.observability.ports as observability_ports
import legoai.reference.observation as observation
import legoai.plugins.values as plugins_values
import legoai.capabilities.values as capabilities_values
import legoai.reference.declarations as declarations
import legoai.reference.resolution as resolution
import legoai.reference.deterministic as deterministic
import legoai.runtime._composition.direct as composition
import legoai.execution.values as execution_values
import legoai.resources.values as resources_values
import legoai.governance.ports as governance_ports
import legoai.reference.governance as reference_governance
import legoai.plugins.ports as plugins_ports
import legoai.reference.plugins as reference_plugins
import legoai.capabilities.ports as capabilities_ports
import legoai.reference.catalog as reference_catalog
import legoai.evidence.ports as evidence_ports
import legoai.reference.evidence as reference_evidence
import legoai.execution.ports as execution_ports
import legoai.reference.execution as reference_execution
for module in (references, context, versions, errors, effects, provenance, governance, evidence, application, ports, configuration, codec, sqlite_store, recovery, observability_values, observability_ports, observation, plugins_values, capabilities_values, declarations, resolution, deterministic, composition, execution_values, resources_values, governance_ports, reference_governance, plugins_ports, reference_plugins, capabilities_ports, reference_catalog, evidence_ports, reference_evidence, execution_ports, reference_execution):
    assert Path(module.__file__).is_relative_to(Path(sys.prefix))
target = references.ConfigurationRef(references.ApplicationRef(references.ReferenceScope("owner", identity.TenantId("t")), identity.ApplicationId("app")), "fixture")
result = configuration.compose_configuration(target, (), contract_version=versions.Version(0, 1, 0), interpretation_version=versions.Version(0, 1, 0))
assert result.effective.max_input_length == 4096
assert versions.Version(0, 1, 0) < versions.Version(0, 2, 0)
assert context.TenantContext(identity.TenantId("t")).tenant_id == identity.TenantId("t")
assert governance.Principal(references.PrincipalRef("issuer", identity.PrincipalId("p"))).reference.principal_id == identity.PrincipalId("p")
grant_principal = governance.Principal(references.PrincipalRef("issuer", identity.PrincipalId("p")))
grant = governance.Grant(governance.GrantId("g1"), grant_principal, grant_principal, context.TenantContext(identity.TenantId("t")), "action", "scope", False, datetime(2026, 1, 1, tzinfo=timezone.utc), None)
assert grant.expires_at is None
policy_ref = governance.PolicyRef("issuer", "policy", versions.Version(1, 0, 0))
assert policy_ref.version == versions.Version(1, 0, 0)
from decimal import Decimal
quantity = resources_values.ResourceQuantity(resources_values.ResourceDimension("compute-seconds"), "second", versions.Version(1, 0, 0), resources_values.ResourceAmountKind.BOUND, Decimal("1"))
resource_operation = references.OperationRef(target, identity.OperationId("res-op"), "smoke")
claim = resources_values.ResourceClaim(resources_values.ResourceClaimId("c1"), resource_operation, context.TenantContext(identity.TenantId("t")), quantity)
assert claim.quantity.magnitude == Decimal("1")
class _AllActive:
    def current_revocation_status(self, grant): return governance_ports.RevocationStatus.ACTIVE
    def current_use_state(self, approval): return governance_ports.ApprovalUseState(approval.approval_id, 0)
    def current_status(self, policy_ref): return governance_ports.PolicyCurrencyStatus.CURRENT
security_context = governance_ports.SecurityContext(grant_principal, context.TenantContext(identity.TenantId("t")), resource_operation, "action", "scope", grant, None, policy_ref, datetime(2026, 1, 1, tzinfo=timezone.utc))
evaluator = reference_governance.DeterministicAuthorizationEvaluator(_AllActive(), _AllActive(), _AllActive())
decision = evaluator.evaluate(security_context)
assert decision.outcome is governance_ports.AuthorizationOutcome.ALLOWED
plugin_declaration = plugins_values.PluginDeclaration(plugins_values.PluginId("legoai", "fixture"), versions.Version(0, 1, 0))
discovered_ref = reference_plugins.inspect(plugin_declaration)
validation_result = reference_plugins.validate(discovered_ref, plugin_declaration, evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
lifecycle_record = reference_plugins.admit(validation_result, context.TenantContext(identity.TenantId("t")), plugins_ports.PluginAdmissionId("a1"), established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
assert lifecycle_record.state is plugins_ports.PluginLifecycleState.VALIDATED
active_declaration = plugins_values.PluginDeclaration(plugins_values.PluginId("legoai", "fixture-2"), versions.Version(0, 1, 0), (capabilities_values.CapabilityOffer(capabilities_values.CapabilityId("text-normalize"), versions.Version(1, 0, 0)),), ())
active_record = plugins_ports.PluginLifecycleRecord(plugins_ports.PluginAdmissionId("a2"), active_declaration.plugin_id, active_declaration.release, context.TenantContext(identity.TenantId("t")), plugins_ports.PluginLifecycleState.ACTIVE, 1, datetime(2026, 1, 1, tzinfo=timezone.utc))
catalog = reference_catalog.InMemoryCatalog()
catalog_entry = catalog.publish(active_record, active_declaration, active_declaration.offers[0], established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
assert catalog_entry in catalog.snapshot(context.TenantContext(identity.TenantId("t"))).entries
requirement = capabilities_values.CapabilityRequirement(capabilities_values.CapabilityId("text-normalize"), capabilities_values.CapabilityVersionRange(versions.Version(1, 0, 0)))
capability_resolution = resolution.resolve(requirement, catalog.snapshot(context.TenantContext(identity.TenantId("t"))), resolved_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
assert capability_resolution.status is resolution.ResolutionStatus.RESOLVED
assert capability_resolution.candidates == (catalog_entry,)
custody = reference_evidence.InMemoryEvidenceCustody()
config_revision_ref = references.ConfigurationRevisionRef(target, "r1", versions.Version(0, 1, 0))
evidence_record = evidence_ports.EvidenceRecord(evidence_ports.EvidenceId("ev1"), config_revision_ref, grant_principal, context.TenantContext(identity.TenantId("t")), "source submitted", datetime(2026, 1, 1, tzinfo=timezone.utc))
custody.record(evidence_record)
assert custody.read(evidence_ports.EvidenceId("ev1"), context.TenantContext(identity.TenantId("t"))) == evidence_record
arbiter = reference_execution.DeterministicDispatchArbiter(evaluator, catalog, custody, _AllActive())
dispatch_request = execution_ports.DispatchRequest(security_context, catalog_entry, (evidence_ports.EvidenceId("ev1"),))
dispatch_decision = arbiter.arbitrate(dispatch_request, evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
assert dispatch_decision.outcome is execution_ports.DispatchOutcome.PERMITTED
assert dispatch_decision.permit is not None
assert dispatch_decision.permit.resolved_entry == catalog_entry
import asyncio
class _FixedResolver:
    async def resolve(self, ref, tenant_context):
        return security_context
execution_context = execution_values.ExecutionContext(
    execution_values.ExecutionId("exec-1"), resource_operation, context.TenantContext(identity.TenantId("t")),
    execution_values.SecurityContextRef("issuer", "ref-1"), identity.CorrelationId("corr-1"), None, None, None,
)
coordination_request = execution_ports.CoordinationRequest(execution_context, catalog_entry)
coordinator = reference_execution.ExecutionCoordinator(_FixedResolver(), arbiter)
coordination_result = asyncio.run(coordinator.coordinate(coordination_request))
assert coordination_result.outcome is execution_ports.CoordinationOutcome.READY
assert coordination_result.state is execution_values.ExecutionState.RUNNING
assert coordination_result.permit is not None
assert coordination_result.permit.resolved_entry == catalog_entry
import legoai.runtime._composition.governed as governed
real_declaration = deterministic.text_normalization_declaration()
real_discovered = reference_plugins.inspect(real_declaration)
real_validation = reference_plugins.validate(real_discovered, real_declaration, evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
real_record = reference_plugins.admit(real_validation, context.TenantContext(identity.TenantId("t")), plugins_ports.PluginAdmissionId("a-real"), established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
real_active = reference_plugins.activate(reference_plugins.initialize(real_record, established_at=datetime(2026, 1, 1, tzinfo=timezone.utc)), established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
real_entry = catalog.publish(real_active, real_declaration, real_declaration.offers[0], established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
real_grant = governance.Grant(governance.GrantId("g-real"), grant_principal, grant_principal, context.TenantContext(identity.TenantId("t")), "action", deterministic.text_normalization_capability_id().value, False, datetime(2026, 1, 1, tzinfo=timezone.utc), None)
real_security_context = governance_ports.SecurityContext(grant_principal, context.TenantContext(identity.TenantId("t")), resource_operation, "action", deterministic.text_normalization_capability_id().value, real_grant, None, policy_ref, datetime(2026, 1, 1, tzinfo=timezone.utc))
class _RealResolver:
    async def resolve(self, ref, tenant_context):
        return real_security_context
real_execution_context = execution_values.ExecutionContext(
    execution_values.ExecutionId("exec-real"), resource_operation, context.TenantContext(identity.TenantId("t")),
    execution_values.SecurityContextRef("issuer", "ref-real"), identity.CorrelationId("corr-real"), None, None, None,
)
real_request = execution_ports.CoordinationRequest(real_execution_context, real_entry)
real_coordinator = reference_execution.ExecutionCoordinator(_RealResolver(), arbiter)
real_coordination = asyncio.run(real_coordinator.coordinate(real_request))
assert real_coordination.outcome is execution_ports.CoordinationOutcome.READY
governed_result = asyncio.run(governed.invoke_governed_text_normalization(real_coordinator, real_coordination, "  hello   world  ", result.effective))
assert governed_result.execution_result.final_state is execution_values.ExecutionState.SUCCEEDED
assert governed_result.execution_result.effect is effects.EffectExtent.COMPLETED
assert governed_result.output == "hello world"
import legoai.intelligence.model.values as model_values
import legoai.intelligence.model.ports as model_ports
import legoai.reference.model as reference_model
import legoai.runtime._composition.model_governed as model_governed
ollama_declaration = reference_model.ollama_declaration()
ollama_discovered = reference_plugins.inspect(ollama_declaration)
ollama_validation = reference_plugins.validate(ollama_discovered, ollama_declaration, evaluated_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
ollama_record = reference_plugins.admit(ollama_validation, context.TenantContext(identity.TenantId("t")), plugins_ports.PluginAdmissionId("a-ollama"), established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
ollama_active = reference_plugins.activate(reference_plugins.initialize(ollama_record, established_at=datetime(2026, 1, 1, tzinfo=timezone.utc)), established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
ollama_entry = catalog.publish(ollama_active, ollama_declaration, ollama_declaration.offers[0], established_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
ollama_grant = governance.Grant(governance.GrantId("g-ollama"), grant_principal, grant_principal, context.TenantContext(identity.TenantId("t")), "action", reference_model.ollama_chat_capability_id().value, False, datetime(2026, 1, 1, tzinfo=timezone.utc), None)
ollama_security_context = governance_ports.SecurityContext(grant_principal, context.TenantContext(identity.TenantId("t")), resource_operation, "action", reference_model.ollama_chat_capability_id().value, ollama_grant, None, policy_ref, datetime(2026, 1, 1, tzinfo=timezone.utc))
class _OllamaResolver:
    async def resolve(self, ref, tenant_context):
        return ollama_security_context
ollama_execution_context = execution_values.ExecutionContext(
    execution_values.ExecutionId("exec-ollama"), resource_operation, context.TenantContext(identity.TenantId("t")),
    execution_values.SecurityContextRef("issuer", "ref-ollama"), identity.CorrelationId("corr-ollama"), None, None, None,
)
ollama_coord_request = execution_ports.CoordinationRequest(ollama_execution_context, ollama_entry)
ollama_coordinator = reference_execution.ExecutionCoordinator(_OllamaResolver(), arbiter)
ollama_coordination = asyncio.run(ollama_coordinator.coordinate(ollama_coord_request))
assert ollama_coordination.outcome is execution_ports.CoordinationOutcome.READY
class _FakeModelPort:
    async def chat(self, request):
        return model_values.ChatResult("fake answer", model_values.ModelId("fake-model"), model_values.ProviderId("fake-provider"), None)
    async def embed(self, request):
        return model_values.EmbeddingResult(((1.0,),), 1, model_values.ModelId("fake-model"), model_values.ProviderId("fake-provider"))
chat_request = model_values.ChatRequest((model_values.ChatMessage(model_values.ChatRole.USER, "hi"),))
model_execution_result, model_chat_result = asyncio.run(
    model_governed.invoke_governed_chat(ollama_coordinator, ollama_coordination, chat_request, _FakeModelPort())
)
assert model_execution_result.final_state is execution_values.ExecutionState.SUCCEEDED
assert model_chat_result.content == "fake answer"
import legoai.intelligence.model.routing as model_routing
import legoai.reference.model_routing as reference_routing
model_revision = references.ConfigurationRevisionRef(target, "models-r1", versions.Version(1, 0, 0))
model_requirement = model_routing.ModelRequirement("engineering-reasoning")
model_binding = model_routing.ModelBinding("fake-binding", model_requirement, model_values.ModelId("fake-model"), model_values.ProviderId("fake-provider"))
router = reference_routing.DeterministicModelRouter(model_revision, (model_binding,))
route = router.route(model_requirement, context.TenantContext(identity.TenantId("t")))
assert route.selected == model_binding
assert route.configuration_revision == model_revision
assert Path(reference_routing.__file__).is_relative_to(Path(sys.prefix))
configured = model_governed.ConfiguredModelBinding(model_revision, model_binding, ollama_entry, _FakeModelPort())
routed_context = execution_values.ExecutionContext(
    execution_values.ExecutionId("exec-routed"), resource_operation, context.TenantContext(identity.TenantId("t")),
    execution_values.SecurityContextRef("issuer", "ref-routed"), identity.CorrelationId("corr-routed"), None, None, None,
)
routed_coordination = asyncio.run(ollama_coordinator.coordinate(execution_ports.CoordinationRequest(routed_context, ollama_entry)))
routed_execution, routed_output = asyncio.run(model_governed.invoke_routed_chat(ollama_coordinator, routed_coordination, chat_request, route, configured))
assert routed_execution.final_state is execution_values.ExecutionState.SUCCEEDED
assert routed_output.content == "fake answer"
import legoai.runtime._composition.model_selection as model_selection
assert Path(model_selection.__file__).is_relative_to(Path(sys.prefix))
desired = model_selection.capture_model_selection({"revision": "models-r1", "binding": "fake-binding"}, pinned_revision=model_revision)
try:
    model_selection.capture_model_selection({"revision": "stale", "binding": "fake-binding"}, pinned_revision=model_revision)
except model_selection.ModelCompositionError as error:
    assert error.failure is model_selection.CompositionFailure.STALE_CONFIGURATION
else:
    raise AssertionError("stale selection accepted")
chat_offer = reference_model.ollama_chat_offer()
chat_requirement = capabilities_values.CapabilityRequirement(chat_offer.capability, capabilities_values.CapabilityVersionRange(chat_offer.version))
contribution = model_selection.ModelContribution(model_revision, model_binding, ollama_entry, ollama_active, _FakeModelPort)
composed = model_selection.compose_model(chat_requirement, desired, catalog=catalog, contributions=(contribution,), resolved_at=datetime(2026, 1, 1, tzinfo=timezone.utc))
assert composed.route.selected == model_binding
assert composed.configured.entry == ollama_entry
selected_coordination = asyncio.run(ollama_coordinator.coordinate(execution_ports.CoordinationRequest(execution_values.ExecutionContext(
    execution_values.ExecutionId("exec-selected"), resource_operation, context.TenantContext(identity.TenantId("t")),
    execution_values.SecurityContextRef("issuer", "ref-selected"), identity.CorrelationId("corr-selected"), None, None, None,
), ollama_entry)))
selected_execution, selected_output = asyncio.run(model_governed.invoke_routed_chat(ollama_coordinator, selected_coordination, chat_request, composed.route, composed.configured))
assert selected_execution.final_state is execution_values.ExecutionState.SUCCEEDED
assert selected_output.content == "fake answer"
assert len(effects.EffectExtent) == 4
assert len(errors.ErrorCategory) == 9
assert Path(identity.__file__).is_relative_to(Path(sys.prefix))
assert identity.TenantId("abc").value == "abc"
assert identity.PrincipalId("abc").value == "abc"
assert version("legoai-reference") == "0.1.0.dev0"
assert not requires("legoai-reference")
assert Path(identity.__file__).parents[1].joinpath("py.typed").is_file()
duty_id = provenance.DutyId("duty-1")
duty_kind = provenance.DutyKind("source-submission")
assert duty_id != duty_kind
evidence_req = evidence.EvidenceRequirement(
    references.ConfigurationRevisionRef(target, "r1", versions.Version(0, 1, 0)),
    "evidence needed",
)
assert evidence_req.description == "evidence needed"
assert len(execution_values.ExecutionState) == 10
assert execution_values.ExecutionId("exec-1").value == "exec-1"
assert hasattr(ports, "ConfigurationStorePort")
assert hasattr(application, "ConfigurationPublicationOperation")
assert hasattr(application, "ConfigurationSourceSubmissionDuty")
head = references.OwnerRevision(target, 1)
head_record = codec.encode_owner_head(head)
assert codec.decode_owner_head(head_record) == head
assert codec.loads(codec.dumps(head_record)) == head_record
store = sqlite_store.SQLiteConfigurationStore(Path.cwd() / "smoke.sqlite3")
principal = governance.Principal(references.PrincipalRef("issuer", identity.PrincipalId("p")))
op = application.ConfigurationPublicationOperation(
    references.OperationRef(target, identity.OperationId("op1"), "smoke"),
    target, None, result, principal,
)
published = store.publish(op)
assert published.stage.value == "committed"
assert store.current_head(target) == published.resulting_revision
report = recovery.qualify_store(Path.cwd() / "smoke.sqlite3")
assert report.status is recovery.RecoveryStatus.QUALIFIED
assert report.integrity_check == "ok"
assert len(report.scopes) == 1
obs = observability_values.Observation(
    1, observability_values.ObservationEventCode("smoke.event"), "smoke-owner"
)
sink = observation.LocalLoggingObservationSink()
sink.emit(obs)
assert isinstance(sink, observability_ports.ObservationSinkPort)
cap_id = capabilities_values.CapabilityId("smoke.capability")
version_range = capabilities_values.CapabilityVersionRange(versions.Version(1, 0, 0))
requirement = capabilities_values.CapabilityRequirement(cap_id, version_range)
offer = capabilities_values.CapabilityOffer(cap_id, versions.Version(1, 0, 0))
plugin_id = plugins_values.PluginId("smoke.namespace", "smoke-plugin")
declaration = plugins_values.PluginDeclaration(
    plugin_id, versions.Version(1, 0, 0), (offer,)
)
analysis = resolution.analyze_compatibility(requirement, (declaration,))
assert analysis.status is resolution.CompatibilityStatus.UNIQUE_MATCH
normalized = declarations.normalize_declarations((declaration,))
assert normalized == (declaration,)
norm_requirement = capabilities_values.CapabilityRequirement(
    deterministic.text_normalization_capability_id(),
    capabilities_values.CapabilityVersionRange(deterministic.text_normalization_release()),
)
composition_result = composition.compose_direct(
    target=target,
    candidates=(),
    contract_version=versions.Version(0, 1, 0),
    interpretation_version=versions.Version(0, 1, 0),
    text="  smoke   test  ",
    requirement=norm_requirement,
    declarations=(deterministic.text_normalization_declaration(),),
)
assert composition_result.status is composition.CompositionStatus.COMPOSED
assert composition_result.normalized_text == "smoke test"
"""
    result = run([str(interpreter), "-I", "-B", "-c", script], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr

    # Execute the shipped example with only the fresh wheel installed, outside
    # the checkout. No source-path fallback or provider service is available.
    example = tmp_path / "model_routing.py"
    example.write_bytes((root / "examples" / "model_routing.py").read_bytes())
    result = run([str(interpreter), "-I", "-B", str(example)], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == [
        "engineering-reasoning: resolved",
        "reasoning-local: demo-provider/demo-model",
        "configuration: r1",
    ]
    agent_example = tmp_path / "agent.py"
    agent_example.write_bytes((root / "examples" / "agent.py").read_bytes())
    result = run([str(interpreter), "-I", "-B", str(agent_example)], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["succeeded", "A bounded Agent result."]

    # ADR-014: the public local host from the installed wheel, public imports
    # only. The consumer module itself never names reference/private wiring.
    host_example = tmp_path / "local_host.py"
    host_example.write_bytes((root / "examples" / "local_host.py").read_bytes())
    assert "legoai.reference" not in host_example.read_text(encoding="utf-8")
    assert "_composition" not in host_example.read_text(encoding="utf-8")
    result = run([str(interpreter), "-I", "-B", str(host_example)], tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.splitlines() == ["succeeded", "A bounded Agent result."]
    public = """
import sys
from pathlib import Path
import legoai.runtime.api as api
import legoai.runtime.local as local
for module in (api, local):
    assert Path(module.__file__).is_relative_to(Path(sys.prefix)), module.__file__
assert callable(local.open_local_host)
assert [p.value for p in api.ModelPurpose] == ["chat", "embedding"]
assert api.HostError(api.HostFailure.CAPACITY_EXHAUSTED).failure.value == "capacity_exhausted"
"""
    result = run([str(interpreter), "-I", "-B", "-c", public], tmp_path)
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
