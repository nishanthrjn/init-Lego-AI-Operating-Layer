"""Offline trusted composition for PROVIDER-MODEL-DISCOVERY-1 tests.

Wires the qualified owners exactly as the private seam expects: one shared
ordering domain, an S1 revision provisioned for the discovery purpose and
consumer with synthetic material, domain-bound registries and Catalog, a
fresh Secret-use ledger, the attempt store and a test TLS trust anchor. No
external network, provider or real credential.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from legoai.capabilities.values import CapabilityId, CapabilityOffer
from legoai.evidence.custody import CustodyAccess
from legoai.governance.provider_control import (
    ProviderDiscoveryAdmission,
    ProviderOperation,
)
from legoai.governance.secret import SecretRef
from legoai.governance.values import Grant, GrantId, PolicyRef, Principal
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import PrincipalId, TenantId
from legoai.kernel.references import PrincipalRef, ReferenceScope
from legoai.kernel.versions import Version
from legoai.plugins.ports import (
    PluginAdmissionId,
    PluginLifecycleRecord,
    PluginLifecycleState,
)
from legoai.plugins.values import PluginDeclaration, PluginId
from legoai.reference._credential_https import tls_context
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._remote_attempts import _RemoteAttemptStore
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.governance import (
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.secret import _ProvisionedSecretSource, _SecretClock
from legoai.runtime._composition.provider_discovery import (
    DiscoveryEndpoint,
    ModelDiscovery,
    discover_remote_models,
    discovery_consumer,
    discovery_purpose,
)
from legoai.runtime._composition.secret import _SecretUses
from tests.integration.composition.test_local_host import REVISION
from tests.support.tls_server import TEST_CA

AT = datetime(2026, 10, 9, 12, tzinfo=UTC)
HOUR = timedelta(hours=1)
SCOPE = ReferenceScope("operator", TenantId("tenant-a"))
PRINCIPAL = Principal(PrincipalRef("operator", PrincipalId("service")))
POLICY = PolicyRef("operator", "policy", Version(1, 0, 0))
CONSUMER = "compat-probe"
PROVIDER = "remote-endpoint"


@dataclass
class Discovery:
    source: _ProvisionedSecretSource
    credential: SecretRef
    origin: str
    admission: ProviderDiscoveryAdmission
    endpoint: DiscoveryEndpoint
    attempts: _RemoteAttemptStore
    uses: _SecretUses
    grants: InMemoryGrantRegistry
    grant: Grant
    directory: Path
    now: datetime

    def clock(self) -> datetime:
        return self.now

    def run(self, **changes: Any) -> ModelDiscovery:
        options: dict[str, Any] = {
            "consumer": CONSUMER,
            "attempts": self.attempts,
            "uses": self.uses,
            "configuration": REVISION,
            "principal": PRINCIPAL,
            "grant": self.grant,
            "policy": POLICY,
            "tls": tls_context(TEST_CA),
            "timeout": 5.0,
            "margin": timedelta(minutes=5),
            "clock": self.clock,
        }
        admission = changes.pop("admission", self.admission)
        endpoint = changes.pop("endpoint", self.endpoint)
        return discover_remote_models(admission, endpoint, **(options | changes))

    @property
    def ledger(self) -> Path:
        return self.directory / "secret-uses" / "source.db"

    def access(self) -> CustodyAccess:
        return CustodyAccess(SCOPE, PRINCIPAL)


@contextmanager
def discovery(
    directory: Path,
    port: int,
    material: str,
    *,
    purpose: str | None = None,
    consumer: str | None = None,
) -> Iterator[Discovery]:
    domain = _OrderingDomain()
    source = _ProvisionedSecretSource(domain, SCOPE)
    credential = source.provision(
        "provider-key",
        purpose or discovery_purpose(),
        consumer or discovery_consumer(),
        material,
    )
    origin = f"https://localhost:{port}"
    admission = ProviderDiscoveryAdmission(
        "discovery",
        "d1",
        PROVIDER,
        origin,
        "/v1",
        ProviderOperation.MODEL_DISCOVERY,
        CONSUMER,
        credential.exact,
        AT - HOUR,
        AT + HOUR,
    )
    tenant = TenantContext(SCOPE.tenant_id)
    grant = Grant(
        GrantId("grant-secret"),
        PRINCIPAL,
        PRINCIPAL,
        tenant,
        "secret-use",
        credential.exact.identity,
        False,
        AT - HOUR,
        AT + 24 * HOUR,
    )
    grants = InMemoryGrantRegistry(_domain=domain)
    catalog = InMemoryCatalog(_domain=domain)
    version = Version(1, 0, 0)
    offer = CapabilityOffer(CapabilityId(discovery_consumer()), version)
    plugin = PluginId("legoai.reference", "openai-compatible-model-adapter")
    declaration = PluginDeclaration(plugin, version, (offer,), ())
    record = PluginLifecycleRecord(
        PluginAdmissionId("discovery-consumer"),
        plugin,
        version,
        tenant,
        PluginLifecycleState.ACTIVE,
        1,
        AT,
    )
    entry = catalog.publish(record, declaration, offer, established_at=AT)
    uses_directory = directory / "secret-uses"
    uses_directory.mkdir()
    _SecretLedger.provision(uses_directory / "source.db")
    _EvidenceStore.provision(uses_directory / "evidence.db")
    access = CustodyAccess(SCOPE, PRINCIPAL)
    ledger = _SecretLedger(uses_directory / "source.db", access, domain)
    evidence = _EvidenceStore(uses_directory / "evidence.db", access, domain)
    attempts_path = directory / "remote-attempts.db"
    _RemoteAttemptStore.provision(attempts_path)
    holder: dict[str, Discovery] = {}
    attempts = _RemoteAttemptStore(attempts_path, domain, lambda: holder["x"].now)
    uses = _SecretUses(
        entry,
        domain,
        grants,
        InMemoryPolicyRegistry(_domain=domain),
        InMemoryApprovalRegistry(_domain=domain),
        catalog,
        ledger,
        evidence,
        _SecretClock(domain, host=lambda: holder["x"].now),
        source,
    )
    x = Discovery(
        source,
        credential,
        origin,
        admission,
        DiscoveryEndpoint(PROVIDER, origin, "/v1", credential),
        attempts,
        uses,
        grants,
        grant,
        directory,
        AT,
    )
    holder["x"] = x
    try:
        yield x
    finally:
        attempts.close()
        evidence.close()
        ledger.close()


def with_admission(x: Discovery, **changes: Any) -> ProviderDiscoveryAdmission:
    return replace(x.admission, **changes)
