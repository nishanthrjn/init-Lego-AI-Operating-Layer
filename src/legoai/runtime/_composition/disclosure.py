"""ADR-024 invocation-time REMOTE disclosure gate (private composition).

Composes the governance evaluator with trusted endpoint facts and Evidence
custody; it holds no policy of its own. The governed Model invocation path
calls it after claiming the invocation and before any adapter call. A refusal
records a safe `DisclosureObservation` and the caller settles NONE without
touching the provider. Recorded Evidence is never read back: it is not
admission state.

No caller in the public host constructs a gate yet: REMOTE bindings are still
refused at open, so LOCAL invocations never reach this module.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from legoai.evidence.ports import EvidenceCustodyPort, EvidenceId, EvidenceRecord
from legoai.execution.values import ExecutionContext
from legoai.governance.disclosure import (
    DisclosureAdmission,
    DisclosureDecision,
    DisclosureDeclaration,
    DisclosureObservation,
    DisclosureRefusal,
    DisclosureRequest,
    ProcessorDeclaration,
    evaluate_disclosure,
)
from legoai.governance.values import Principal
from legoai.kernel.effects import EffectExtent


@dataclass(frozen=True, slots=True)
class RemoteEndpointFacts:
    """Trusted facts of the selected REMOTE binding, taken from its settings.

    Never derived from requests, responses or content.
    """

    binding_id: str = field(repr=False)
    provider_id: str = field(repr=False)
    endpoint_origin: str = field(repr=False)
    api_root: str = field(repr=False)
    chat_model: str = field(repr=False)
    embedding_model: str | None = field(repr=False)

    def model_for(self, purpose: str) -> str | None:
        return self.chat_model if purpose == "chat" else self.embedding_model


@dataclass(frozen=True, slots=True)
class RemoteDisclosureGate:
    """One host's gate: its pinned configuration, endpoint facts and custody.

    Currentness: every check evaluates this host's configured admissions and
    declarations at the clock's current time. A changed configuration is a new
    configuration revision and therefore a new host (ADR-003).
    """

    endpoint: RemoteEndpointFacts
    declarations: tuple[ProcessorDeclaration, ...] = field(repr=False)
    admissions: tuple[DisclosureAdmission, ...] = field(repr=False)
    custody: EvidenceCustodyPort = field(repr=False)
    issuer: Principal = field(repr=False)
    clock: Callable[[], datetime] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.endpoint) is not RemoteEndpointFacts:
            raise TypeError("gate requires RemoteEndpointFacts")
        if type(self.declarations) is not tuple or type(self.admissions) is not tuple:
            raise TypeError("gate requires configured tuples")
        if type(self.issuer) is not Principal or not callable(self.clock):
            raise TypeError("gate requires an issuer and a clock")


@dataclass(frozen=True, slots=True)
class DisclosureCheck:
    """The gate bound to one minted execution and its trusted declaration.

    `declaration`/`consumer` come only from the host's minted state for this
    exact execution; None means the caller declared nothing (UNCLASSIFIED).
    """

    gate: RemoteDisclosureGate
    context: ExecutionContext
    purpose: str
    consumer: str | None = field(repr=False)
    declaration: DisclosureDeclaration | None = field(repr=False)

    def decide(self) -> DisclosureDecision:
        if self.declaration is None or self.consumer is None:
            # Nothing was declared for this execution: never inferred.
            return DisclosureDecision(DisclosureRefusal.UNCLASSIFIED)
        endpoint = self.gate.endpoint
        model = endpoint.model_for(self.purpose)
        if model is None:
            return DisclosureDecision(DisclosureRefusal.PURPOSE_MISMATCH)
        request = DisclosureRequest(
            endpoint.binding_id,
            endpoint.provider_id,
            endpoint.endpoint_origin,
            endpoint.api_root,
            True,  # the gate exists only for REMOTE-declared bindings
            model,
            self.consumer,
            self.purpose,
            self.declaration,
            self.gate.clock(),
        )
        return evaluate_disclosure(
            request, self.gate.admissions, self.gate.declarations
        )

    def evidence_id(self) -> EvidenceId:
        return EvidenceId(f"disclosure-{self.context.execution_id.value}")

    def observe(self, decision: DisclosureDecision, effect: EffectExtent) -> EvidenceId:
        """Record the safe observation for this execution (ADR-009 custody).

        Custody failures propagate; they are never swallowed.
        """
        endpoint = self.gate.endpoint
        declaration = self.declaration
        admission = next(
            (
                a
                for a in self.gate.admissions
                if a.admission_id == decision.admission_id
            ),
            None,
        )
        observation = DisclosureObservation(
            self.context.operation,
            endpoint.binding_id,
            endpoint.provider_id,
            endpoint.endpoint_origin,
            endpoint.model_for(self.purpose) or endpoint.chat_model,
            self.purpose,
            self.consumer,
            declaration.classes if declaration is not None else frozenset(),
            declaration.repository if declaration is not None else None,
            decision.admission_id,
            decision.admission_revision,
            admission.declaration_id if admission is not None else None,
            decision.declaration_revision,
            decision.refusal,
            effect,
            self.gate.clock(),
        )
        record = EvidenceRecord(
            self.evidence_id(),
            observation,
            self.gate.issuer,
            self.context.tenant_context,
            "model-disclosure/1 observation",
            observation.observed_at,
        )
        return self.gate.custody.record(record).evidence_id
