"""OPENAI-COMPATIBLE-REMOTE-1: the Model invocation plane of one REMOTE binding.

Joins the qualified mechanisms behind the existing OpenAI-compatible adapter;
it owns no disclosure policy, Secret policy, TLS or wire parsing. Per governed
invocation, after the governed path has an ADMITTED disclosure decision:

    credential association check -> exact RemoteAttempt -> durable INTENDED
    -> a new exact Secret use for THIS invocation (use id = attempt id)
    -> Secret currentness before transport -> T2 exchange (verified TLS, one
    handoff claim, final currentness under the ordering domain, gated writes,
    bounded response) -> attempt settlement -> the adapter's shared parser.

No step authorizes the next by existing. Any refusal before the handoff
claim settles the attempt NOT_SENT and sends nothing; nothing is retried,
resent or routed elsewhere. The exchange runs on the host's confined thread
(owner-local SQLite custody and the Secret owner are thread-confined), so it
blocks that thread's event loop for at most the binding's timeout; asyncio
cancellation is observed before the exchange begins or after it settles,
never in the middle, and never rewrites recorded truth.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from secrets import token_hex
from ssl import SSLContext

from legoai.capabilities.ports import CatalogEntry
from legoai.capabilities.values import CapabilityId
from legoai.evidence.custody import CustodyAccess
from legoai.governance.disclosure import DisclosureDecision
from legoai.governance.ports import SecretAccessRequest, SecurityContext
from legoai.governance.secret import SecretRef, SecretUseId, SecretUsePlan
from legoai.governance.values import Grant, PolicyRef, Principal
from legoai.intelligence.model.ports import (
    ModelPort,
    ModelPreflightError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.values import (
    ChatRequest,
    ChatResult,
    EmbeddingRequest,
    EmbeddingResult,
)
from legoai.kernel.context import TenantContext
from legoai.kernel.identity import RequestId
from legoai.kernel.references import (
    ConfigurationRevisionRef,
    OperationRef,
)
from legoai.kernel.versions import Version
from legoai.reference._credential_https import HttpsTarget, TransportError, tls_context
from legoai.reference._durable_evidence import _EvidenceStore
from legoai.reference._remote_attempts import (
    AttemptObservation,
    AttemptState,
    IntendedReceipt,
    RemoteAttemptId,
    _RemoteAttemptStore,
)
from legoai.reference._secret_domain import _OrderingDomain
from legoai.reference._secret_ledger import _SecretLedger
from legoai.reference.catalog import InMemoryCatalog
from legoai.reference.governance import (
    InMemoryApprovalRegistry,
    InMemoryGrantRegistry,
    InMemoryPolicyRegistry,
)
from legoai.reference.model_capabilities import model_chat_offer, model_embedding_offer
from legoai.reference.secret import _ProvisionedSecretSource, _SecretClock
from legoai.runtime._composition.credential_https import exchange
from legoai.runtime._composition.disclosure import DisclosureCheck
from legoai.runtime._composition.remote_attempt import prepare_attempt
from legoai.runtime._composition.secret import _SecretUses

type Exchange = Callable[[str, bytes], tuple[int, bytes]]


def credential_purpose() -> str:
    """The SecretRef use requirement of a REMOTE Model Bearer credential."""
    return "remote-model-bearer"


def credential_consumer() -> str:
    """The protected consumer an S1 revision must be provisioned for."""
    return "legoai.intelligence.model.remote-credential"


def credential_consumer_version() -> Version:
    return Version(1, 0, 0)


def _use_window() -> timedelta:
    """Upper bound of one use's locally asserted validity (plan expiry)."""
    return timedelta(days=1)


@dataclass(frozen=True, slots=True)
class CredentialAssociation:
    """Trusted composition fact: this credential revision serves exactly this
    binding, provider and https recipient for the REMOTE Model purpose.

    Established at host open from the operator's configuration. The S1
    source stays provider-neutral; the association lives only here and is
    re-verified against every attempt and transport target before use.
    """

    credential: SecretRef = field(repr=False)
    binding_id: str = field(repr=False)
    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.credential) is not SecretRef:
            raise TypeError("association requires SecretRef")
        if self.credential.use_requirement != credential_purpose():
            raise ValueError("credential purpose mismatch")


class RemoteModelPlane:
    """Per-host REMOTE Model invocation plane; one exchange per invocation."""

    def __init__(
        self,
        *,
        association: CredentialAssociation,
        attempts: _RemoteAttemptStore,
        uses: _SecretUses,
        configuration: ConfigurationRevisionRef,
        principal: Principal,
        grant: Grant,
        policy: PolicyRef,
        tls: SSLContext,
        timeout: float,
        margin: timedelta,
        clock: Callable[[], datetime],
        adapter: Callable[[Exchange], ModelPort],
    ) -> None:
        self._association = association
        self._attempts, self._uses = attempts, uses
        self._configuration, self._principal = configuration, principal
        self._grant, self._policy = grant, policy
        self._tls, self._timeout, self._margin = tls, timeout, margin
        self._clock, self._adapter = clock, adapter

    def __repr__(self) -> str:
        return "RemoteModelPlane(<binding>)"

    async def chat(
        self, check: DisclosureCheck, decision: DisclosureDecision, request: ChatRequest
    ) -> ChatResult:
        invocation = _Invocation(self, check, decision, model_chat_offer().capability)
        return await self._adapter(invocation.exchange).chat(request)

    async def embed(
        self,
        check: DisclosureCheck,
        decision: DisclosureDecision,
        request: EmbeddingRequest,
    ) -> EmbeddingResult:
        invocation = _Invocation(
            self, check, decision, model_embedding_offer().capability
        )
        return await self._adapter(invocation.exchange).embed(request)


class _Invocation:
    """One governed invocation's single exchange; never called twice."""

    def __init__(
        self,
        plane: RemoteModelPlane,
        check: DisclosureCheck,
        decision: DisclosureDecision,
        capability: CapabilityId,
    ) -> None:
        if (
            type(check) is not DisclosureCheck
            or type(decision) is not DisclosureDecision
        ):
            raise TypeError("an admitted disclosure check is required")
        if not decision.admitted:
            raise PermissionError("remote invocation requires admitted disclosure")
        self._plane, self._check, self._decision = plane, check, decision
        self._capability = capability
        self._used = False

    def exchange(self, path: str, body: bytes) -> tuple[int, bytes]:
        if self._used:
            raise ModelPreflightError("one remote request per invocation")
        self._used = True
        plane = self._plane
        association = plane._association
        endpoint = self._check.gate.endpoint
        recipient = (
            association.binding_id,
            association.provider_id,
            association.endpoint_origin,
            association.api_root,
        )
        try:
            # Association before custody, Secret or transport: the admitted
            # processor, the attempt and the TLS target must all be the one
            # recipient this credential revision was configured for.
            if (
                endpoint.binding_id,
                endpoint.provider_id,
                endpoint.endpoint_origin,
                endpoint.api_root,
            ) != recipient:
                raise PermissionError("credential association mismatch")
            attempt = prepare_attempt(
                self._check,
                self._decision,
                RemoteAttemptId(f"attempt-{token_hex(16)}"),
                plane._configuration,
                self._capability,
                association.credential.exact,
                plane._clock(),
            )
            target = HttpsTarget.for_endpoint(
                association.endpoint_origin, association.api_root, path
            )
            if (
                attempt.binding_id,
                attempt.provider_id.value,
                attempt.endpoint_origin,
                attempt.api_root,
            ) != recipient or (target.origin, target.api_root) != recipient[2:]:
                raise PermissionError("credential association mismatch")
        except (PermissionError, TransportError, TypeError, ValueError) as error:
            raise ModelPreflightError(
                "remote request refused before custody"
            ) from error
        try:
            receipt = plane._attempts.intend(attempt)
        except Exception as error:
            # No INTENDED receipt: no Secret use, no connection, nothing sent.
            raise ModelPreflightError("remote attempt custody unavailable") from error
        try:
            request = self._secret_request(attempt.attempt_id)
            access = plane._uses.admit(request)
            # Current Secret authority before any connection; the final
            # check is repeated inside the ordering domain at the handoff.
            access.authorize_secret_use(request)
        except Exception as error:
            plane._attempts.settle(
                receipt,
                AttemptState.NOT_SENT,
                frozenset({AttemptObservation.REFUSED_AT_GATE}),
            )
            raise ModelPreflightError("remote credential use refused") from error
        try:
            observation, status = exchange(
                plane._attempts,
                receipt,
                access,
                request,
                target,
                plane._tls,
                body,
                timeout=plane._timeout,
                margin=plane._margin,
            )
        except Exception as error:
            raise self._unsettled(receipt) from error
        if status.state is AttemptState.NOT_SENT:
            raise ModelPreflightError("Model request not sent")
        if status.state is AttemptState.UNKNOWN:
            raise ModelResponseUncertainError("Model transport uncertain")
        response = observation.response
        assert response is not None  # COMPLETED/PROVIDER_REJECTED are complete
        return response.status, response.body

    def _secret_request(self, attempt_id: RemoteAttemptId) -> SecretAccessRequest:
        """A new exact use for this invocation, bound to its attempt id."""
        plane = self._plane
        credential = plane._association.credential
        context = self._check.context
        now = plane._clock()
        # The use is valid only while its Grant and the execution deadline are.
        expires = now + _use_window()
        for bound in (plane._grant.expires_at, context.deadline):
            if bound is not None:
                expires = min(expires, bound)
        key = attempt_id.value
        plan = SecretUsePlan(
            SecretUseId(key),
            context.operation.operation_id,
            credential.exact,
            plane._principal,
            plane._principal,
            plane._configuration,
            credential_purpose(),
            credential_consumer(),
            credential_consumer_version(),
            plane._association.binding_id,
            plane._grant.grant_id,
            plane._policy,
            None,
            f"duty-{key}",
            RequestId(f"pre-{key}"),
            RequestId(f"post-{key}"),
            now,
            expires,
            expires + _use_window(),
        )
        security = SecurityContext(
            plane._principal,
            TenantContext(credential.exact.scope.tenant_id),
            OperationRef(
                plane._configuration.configuration,
                context.operation.operation_id,
                credential_purpose(),
            ),
            "secret-use",
            credential.exact.identity,
            plane._grant,
            None,
            plane._policy,
            now,
        )
        return SecretAccessRequest(credential, plan, security)

    def _unsettled(self, receipt: IntendedReceipt) -> Exception:
        """An exchange fault: record only what is known, never NOT_SENT after
        the handoff claim. If recording fails, INTENDED stays (effectively
        UNKNOWN) for inspection."""
        store = self._plane._attempts
        key = receipt.attempt.attempt_id.value
        claimed = key in store._claimed
        if key in store._live:
            try:
                if claimed:
                    store.settle(receipt, AttemptState.UNKNOWN, frozenset())
                else:
                    store.settle(
                        receipt,
                        AttemptState.NOT_SENT,
                        frozenset({AttemptObservation.REFUSED_AT_GATE}),
                    )
            except Exception:
                return ModelResponseUncertainError("remote attempt requires inspection")
        if claimed:
            return ModelResponseUncertainError("Model transport uncertain")
        return ModelPreflightError("Model request not sent")


def compose_remote_plane(
    *,
    association: CredentialAssociation,
    source: _ProvisionedSecretSource,
    custody: Path,
    trust_anchor: Path | None,
    margin: timedelta,
    timeout: float,
    clock: Callable[[], datetime],
    configuration: ConfigurationRevisionRef,
    principal: Principal,
    grant: Grant,
    policy: PolicyRef,
    registries: tuple[
        InMemoryGrantRegistry, InMemoryPolicyRegistry, InMemoryApprovalRegistry
    ],
    consumer: tuple[InMemoryCatalog, CatalogEntry],
    adapter: Callable[[Exchange], ModelPort],
) -> RemoteModelPlane:
    """Open owner-local custody and the per-invocation Secret-use factory.

    Local only: reads the trust store or anchor and opens SQLite custody in
    `custody`. No DNS, connection, TLS, Secret realization or request.
    The attempt store persists across hosts (single writer); each host gets
    a freshly provisioned Secret-use ledger, because a reopened ledger
    admits repair only. Material never persists anywhere.
    """
    domain = source._domain
    if type(domain) is not _OrderingDomain:
        raise TypeError("shared ordering domain required")
    tls = tls_context(trust_anchor)
    attempts_path = custody / "remote-attempts.db"
    if not attempts_path.exists():
        _RemoteAttemptStore.provision(attempts_path)
    uses_directory = custody / f"secret-uses-{token_hex(8)}"
    uses_directory.mkdir()
    ledger_path = uses_directory / "source.db"
    evidence_path = uses_directory / "evidence.db"
    _SecretLedger.provision(ledger_path)
    _EvidenceStore.provision(evidence_path)
    access = CustodyAccess(association.credential.exact.scope, principal)
    attempts = _RemoteAttemptStore(attempts_path, domain, clock)
    try:
        ledger = _SecretLedger(ledger_path, access, domain)
        try:
            evidence = _EvidenceStore(evidence_path, access, domain)
        except BaseException:
            ledger.close()
            raise
    except BaseException:
        attempts.close()
        raise
    catalog, entry = consumer
    grants, policies, approvals = registries
    uses = _SecretUses(
        entry,
        domain,
        grants,
        policies,
        approvals,
        catalog,
        ledger,
        evidence,
        _SecretClock(domain, host=clock),
        source,
    )
    return RemoteModelPlane(
        association=association,
        attempts=attempts,
        uses=uses,
        configuration=configuration,
        principal=principal,
        grant=grant,
        policy=policy,
        tls=tls,
        timeout=timeout,
        margin=margin,
        clock=clock,
        adapter=adapter,
    )
