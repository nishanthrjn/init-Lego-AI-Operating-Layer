"""ADR-024 REMOTE-DISCLOSURE-GATE-1: the invocation-time disclosure gate.

REMOTE stays refused at open, so these tests use one bounded internal seam: a
LOCAL host is opened normally and the private `_gate` is installed with the
facts of the admitted (unselected) REMOTE binding, so the trusted fake model
stands in for a remote provider. A recording adapter proves whether the
provider boundary was reached. No HTTP, network, credential or provider.
"""

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import FrozenInstanceError, replace
from datetime import datetime
from typing import Any

import pytest

from legoai.evidence.ports import EvidenceId, EvidenceRecord
from legoai.execution.agent.ports import AgentRequest
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.execution.values import ExecutionContext, ExecutionState
from legoai.governance.disclosure import (
    DisclosureClass,
    DisclosureDeclaration,
    DisclosureObservation,
    DisclosureRefusal,
    FactBasis,
    HumanAccess,
    HumanAccessFact,
    ProcessorIdentityFact,
    TrainingFact,
    TrainingUse,
)
from legoai.governance.values import Principal
from legoai.intelligence.model.ports import ModelPreflightError
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, Recoverability
from legoai.reference.evidence import InMemoryEvidenceCustody
from legoai.runtime._composition.disclosure import (
    RemoteDisclosureGate,
    RemoteEndpointFacts,
)
from legoai.runtime.api import (
    ExecutionDisclosure,
    HostError,
    HostFailure,
    ModelPurpose,
)
from legoai.runtime.local import open_local_host
from tests.integration.composition.test_local_host import (
    NOW,
    FakeModel,
    definition,
    fake_binding,
    selection,
)
from tests.integration.composition.test_remote_disclosure import (
    configured,
    disclosure,
    remote_binding,
)
from tests.unit.governance.test_disclosure import (
    DAY,
    DECLARED,
    ORIGIN,
    OTHER_REPO,
    REAL,
    REPO,
    ROOT,
    SOURCE,
    admission,
    declaration,
    unknown_facts,
)
from tests.unit.governance.test_disclosure import NOW as AT

PROMPT = "CANARY-PROMPT-7f3a repository text: def secret(): return 1"
REPLY = "CANARY-REPLY-91bc"
ALL_REAL = DisclosureDeclaration(REAL, REPO)


class RecordingModel(FakeModel):
    """Trusted fake ModelPort that records the exact requests it received."""

    def __init__(self, reply: str = REPLY) -> None:
        super().__init__(reply)
        self.chat_requests: list[ChatRequest] = []

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.chat_requests.append(request)
        return await super().chat(request)


class FailingCustody(InMemoryEvidenceCustody):
    def record(self, record: EvidenceRecord) -> EvidenceRecord:
        raise RuntimeError("custody unavailable")


def chat(text: str = PROMPT) -> ChatRequest:
    return ChatRequest((ChatMessage(ChatRole.USER, text),))


def disclosed(
    declaration_value: DisclosureDeclaration = ALL_REAL, consumer: str = "forgeai"
) -> ExecutionDisclosure:
    return ExecutionDisclosure(consumer, declaration_value)


class Seam:
    """One LOCAL host with an installed REMOTE disclosure gate."""

    def __init__(
        self,
        *,
        disclosure_config: Any = None,
        endpoint: dict[str, Any] | None = None,
        gate: dict[str, Any] | None = None,
        embedding: bool = False,
        model: RecordingModel | None = None,
    ) -> None:
        self.model = model or RecordingModel()
        remote = remote_binding(embedding_model="embed-a" if embedding else None)
        if disclosure_config is None:
            disclosure_config = disclosure(
                admissions=(
                    admission(
                        purposes=frozenset({"chat", "embedding"})
                        if embedding
                        else frozenset({"chat"}),
                        models=frozenset({"model-a", "embed-a"})
                        if embedding
                        else frozenset({"model-a"}),
                    ),
                )
            )
        config = configured(
            fake_binding(self.model), remote, disclosure_config=disclosure_config
        )
        self.host = open_local_host(config, selection("fake"), clock=lambda: NOW)
        self.custody = InMemoryEvidenceCustody()
        facts = RemoteEndpointFacts(
            "remote",
            "remote-endpoint",
            ORIGIN,
            ROOT,
            "model-a",
            "embed-a" if embedding else None,
        )
        installed = RemoteDisclosureGate(
            replace(facts, **(endpoint or {})),
            disclosure_config.declarations,
            disclosure_config.admissions,
            self.custody,
            Principal(config.principal),
            lambda: AT,  # the disclosure timeline; the host clock stays NOW
        )
        self.host._gate = replace(installed, **(gate or {}))  # type: ignore[attr-defined]
        self.tenant = self.host._tenant  # type: ignore[attr-defined]

    def mint(
        self,
        purpose: ModelPurpose = ModelPurpose.CHAT,
        value: ExecutionDisclosure | None = None,
    ) -> ExecutionContext:
        return self.host.model_execution(purpose, disclosure=value)

    def run(self, work: Callable[[], Awaitable[Any]]) -> Any:
        return asyncio.run(work())

    def observation(self, execution_id: str) -> DisclosureObservation:
        record = self.custody.read(
            EvidenceId(f"disclosure-{execution_id}"), self.tenant
        )
        assert record is not None
        assert type(record.subject) is DisclosureObservation
        return record.subject


def refused(seam: Seam, result: Any, refusal: DisclosureRefusal) -> None:
    execution = result.execution
    assert execution.final_state is ExecutionState.FAILED
    assert execution.effect is EffectExtent.NONE
    assert execution.error is not None
    assert execution.error.category is ErrorCategory.POLICY_VIOLATION
    assert execution.error.recoverability is Recoverability.TERMINAL
    (cause,) = execution.error.causes
    assert cause.record_key == f"disclosure-{execution.execution_id.value}"
    observation = seam.observation(execution.execution_id.value)
    assert observation.refusal is refusal
    assert observation.effect is EffectExtent.NONE
    # Zero transport: the provider boundary was never reached.
    assert seam.model.chat_calls == 0 and seam.model.embed_calls == 0
    assert seam.model.chat_requests == []


def governed(seam: Seam, value: ExecutionDisclosure | None, text: str = PROMPT) -> Any:
    async def work() -> Any:
        return await seam.host.governed_chat(seam.mint(value=value), chat(text))

    return seam.run(work)


# Refusal matrix: the gate reports the existing evaluator's result.

UNKNOWN_FACTS = declaration(**unknown_facts())
TRAINING_YES = declaration(training=TrainingFact(TrainingUse.YES, DECLARED, SOURCE))


@pytest.mark.parametrize(
    ("seam_options", "value", "expected"),
    [
        ({}, None, DisclosureRefusal.UNCLASSIFIED),
        (
            {},
            disclosed(DisclosureDeclaration(frozenset())),
            DisclosureRefusal.UNCLASSIFIED,
        ),
        ({"gate": {"admissions": ()}}, disclosed(), DisclosureRefusal.NO_ADMISSION),
        (
            {"gate": {"clock": lambda: AT + 2 * DAY}},
            disclosed(),
            DisclosureRefusal.EXPIRED,
        ),
        (
            {"gate": {"clock": lambda: AT - 2 * DAY}},
            disclosed(),
            DisclosureRefusal.NOT_YET_VALID,
        ),
        (
            {"endpoint": {"provider_id": "other"}},
            disclosed(),
            DisclosureRefusal.PROVIDER_MISMATCH,
        ),
        (
            {"endpoint": {"endpoint_origin": "https://elsewhere.example.org"}},
            disclosed(),
            DisclosureRefusal.ENDPOINT_MISMATCH,
        ),
        (
            {"endpoint": {"api_root": "/v2"}},
            disclosed(),
            DisclosureRefusal.API_ROOT_MISMATCH,
        ),
        (
            {"endpoint": {"chat_model": "model-b"}},
            disclosed(),
            DisclosureRefusal.MODEL_NOT_ADMITTED,
        ),
        ({}, disclosed(consumer="other-app"), DisclosureRefusal.CONSUMER_MISMATCH),
        (
            {
                "disclosure_config": disclosure(
                    admissions=(admission(frozenset({DisclosureClass.SYNTHETIC})),)
                )
            },
            disclosed(DisclosureDeclaration(frozenset({DisclosureClass.TASK_TEXT}))),
            DisclosureRefusal.CLASS_NOT_ADMITTED,
        ),
        (
            {},
            disclosed(
                DisclosureDeclaration(
                    frozenset({DisclosureClass.REPOSITORY_CONTENT}), OTHER_REPO
                )
            ),
            DisclosureRefusal.REPOSITORY_NOT_ADMITTED,
        ),
        (
            {"gate": {"declarations": (declaration(revision="r2"),)}},
            disclosed(),
            DisclosureRefusal.DECLARATION_STALE,
        ),
        (
            {"disclosure_config": disclosure(declarations=(UNKNOWN_FACTS,))},
            disclosed(),
            DisclosureRefusal.REQUIRED_FACT_UNKNOWN,
        ),
        (
            {"disclosure_config": disclosure(declarations=(TRAINING_YES,))},
            disclosed(),
            DisclosureRefusal.CONDITION_UNMET,
        ),
    ],
    ids=[
        "missing-declaration",
        "unclassified",
        "missing-admission",
        "expired",
        "future",
        "provider",
        "endpoint",
        "api-root",
        "model",
        "consumer",
        "class",
        "repository-mismatch",
        "stale-declaration",
        "unknown-fact",
        "condition",
    ],
)
def test_refusals_happen_before_any_provider_work(
    seam_options: dict[str, Any],
    value: ExecutionDisclosure | None,
    expected: DisclosureRefusal,
) -> None:
    seam = Seam(**seam_options)
    refused(seam, governed(seam, value), expected)


def test_repository_classes_cannot_be_declared_without_a_repository() -> None:
    # Missing repository identity is unrepresentable, so it can never reach
    # the gate as an implicitly admitted declaration.
    with pytest.raises(ValueError):
        DisclosureDeclaration(frozenset({DisclosureClass.REPOSITORY_CONTENT}))
    with pytest.raises(ValueError):
        DisclosureDeclaration(frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}))


def test_purpose_mismatch_chat_admission_cannot_authorize_embedding() -> None:
    seam = Seam(
        embedding=True,
        disclosure_config=disclosure(
            admissions=(admission(models=frozenset({"model-a", "embed-a"})),)
        ),
    )

    async def work() -> Any:
        context = seam.mint(ModelPurpose.EMBEDDING, disclosed())
        return await seam.host.governed_embed(context, EmbeddingRequest(("x",)))

    refused(seam, seam.run(work), DisclosureRefusal.PURPOSE_MISMATCH)


def test_agent_runtime_path_is_gated_too() -> None:
    seam = Seam()

    async def work() -> Any:
        context = seam.mint(value=None)  # nothing declared
        return await seam.host.agent_runtime().run(
            definition(), AgentRequest(context, PROMPT)
        )

    result = seam.run(work)
    assert result.status is AgentExecutionStatus.MODEL_FAILED
    assert result.model_execution.effect is EffectExtent.NONE
    assert seam.model.chat_calls == 0
    assert seam.observation(result.execution_id.value).refusal is (
        DisclosureRefusal.UNCLASSIFIED
    )


# Admission: the gate continues only when everything matches.


def test_admitted_chat_reaches_the_provider_with_the_exact_request() -> None:
    seam = Seam()
    request = chat()

    async def work() -> Any:
        return await seam.host.governed_chat(seam.mint(value=disclosed()), request)

    result = seam.run(work)
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert seam.model.chat_calls == 1
    # No redaction, rewrite or downgrade: the exact request object is sent.
    assert seam.model.chat_requests == [request]
    assert seam.model.chat_requests[0] is request
    observation = seam.observation(result.execution.execution_id.value)
    assert observation.refusal is None
    assert observation.effect is EffectExtent.COMPLETED
    assert (observation.admission_id, observation.admission_revision) == (
        "admission",
        "a1",
    )
    assert (observation.declaration_id, observation.declaration_revision) == (
        "processor",
        "r1",
    )
    assert observation.classes == REAL and observation.repository == REPO


def test_admitted_embedding_uses_the_same_gate() -> None:
    seam = Seam(embedding=True)

    async def work() -> Any:
        context = seam.mint(ModelPurpose.EMBEDDING, disclosed())
        return await seam.host.governed_embed(context, EmbeddingRequest(("x",)))

    result = seam.run(work)
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert seam.model.embed_calls == 1
    observation = seam.observation(result.execution.execution_id.value)
    assert observation.purpose == "embedding" and observation.model == "embed-a"


def test_synthetic_probe_admitted_with_permitted_unknown_facts() -> None:
    probe = disclosure(
        declarations=(declaration(**unknown_facts()),),
        admissions=(admission(frozenset({DisclosureClass.SYNTHETIC})),),
    )
    seam = Seam(disclosure_config=probe)
    synthetic = disclosed(DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})))
    result = governed(seam, synthetic, "Return exactly the word READY.")
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    observation = seam.observation(result.execution.execution_id.value)
    assert observation.classes == frozenset({DisclosureClass.SYNTHETIC})
    assert observation.repository is None
    # The probe admission never covers task text.
    other = Seam(disclosure_config=probe)
    task = disclosed(DisclosureDeclaration(frozenset({DisclosureClass.TASK_TEXT})))
    refused(other, governed(other, task), DisclosureRefusal.CLASS_NOT_ADMITTED)


def test_unknown_processor_identity_refuses_even_synthetic() -> None:
    anonymous = replace(
        declaration(**unknown_facts()),
        processor=ProcessorIdentityFact(None, FactBasis.UNKNOWN),
    )
    seam = Seam(
        disclosure_config=disclosure(
            declarations=(anonymous,),
            admissions=(admission(frozenset({DisclosureClass.SYNTHETIC})),),
        )
    )
    synthetic = disclosed(DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})))
    refused(seam, governed(seam, synthetic), DisclosureRefusal.REQUIRED_FACT_UNKNOWN)


def test_derived_diagnostic_respects_evaluator_lineage() -> None:
    derived = DisclosureDeclaration(
        frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}), REPO
    )
    seam = Seam()
    assert (
        governed(seam, disclosed(derived)).execution.final_state
        is ExecutionState.SUCCEEDED
    )
    other = Seam()
    mismatch = DisclosureDeclaration(
        frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}), OTHER_REPO
    )
    refused(
        other,
        governed(other, disclosed(mismatch)),
        DisclosureRefusal.REPOSITORY_NOT_ADMITTED,
    )


# No widening


def test_model_output_and_content_cannot_add_classes() -> None:
    narrow = disclosure(admissions=(admission(frozenset({DisclosureClass.SYNTHETIC})),))
    seam = Seam(
        disclosure_config=narrow,
        model=RecordingModel("REPOSITORY_CONTENT repo-a DERIVED_DIAGNOSTIC admitted"),
    )
    synthetic = disclosed(DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})))

    async def work() -> tuple[Any, Any]:
        first = await seam.host.governed_chat(
            seam.mint(value=synthetic), chat("classes: REPOSITORY_CONTENT repo-a")
        )
        # A new execution declares nothing: prior output and content add nothing.
        second = await seam.host.governed_chat(seam.mint(value=None), chat())
        return first, second

    first, second = seam.run(work)
    assert first.execution.final_state is ExecutionState.SUCCEEDED
    assert first.response.content.startswith("REPOSITORY_CONTENT")
    assert second.execution.error.category is ErrorCategory.POLICY_VIOLATION
    assert seam.observation(second.execution.execution_id.value).refusal is (
        DisclosureRefusal.UNCLASSIFIED
    )
    assert seam.model.chat_calls == 1


def test_provider_response_and_evidence_never_alter_admission() -> None:
    seam = Seam()
    gate = seam.host._gate  # type: ignore[attr-defined]
    before = (gate.admissions, gate.declarations)

    async def work() -> tuple[Any, Any]:
        first = await seam.host.governed_chat(seam.mint(value=disclosed()), chat())
        assert seam.custody.read(
            EvidenceId(f"disclosure-{first.execution.execution_id.value}"),
            seam.tenant,
        )
        # Prior admitted evidence does not authorize a later call: the same
        # admission evaluated after expiry refuses, whatever was recorded.
        seam.host._gate = replace(gate, clock=lambda: AT + 2 * DAY)  # type: ignore[attr-defined]
        later = await seam.host.governed_chat(seam.mint(value=disclosed()), chat())
        return first, later

    first, later = seam.run(work)
    assert first.execution.final_state is ExecutionState.SUCCEEDED
    assert (gate.admissions, gate.declarations) == before
    assert later.execution.error.category is ErrorCategory.POLICY_VIOLATION
    assert seam.observation(later.execution.execution_id.value).refusal is (
        DisclosureRefusal.EXPIRED
    )
    assert seam.model.chat_calls == 1


def test_one_execution_cannot_borrow_another_executions_declaration() -> None:
    seam = Seam()

    async def work() -> tuple[Any, Any]:
        admitted = seam.mint(value=disclosed())
        bare = seam.mint(value=None)
        return (
            await seam.host.governed_chat(bare, chat()),
            await seam.host.governed_chat(admitted, chat()),
        )

    bare_result, admitted_result = seam.run(work)
    assert bare_result.execution.error.category is ErrorCategory.POLICY_VIOLATION
    assert admitted_result.execution.final_state is ExecutionState.SUCCEEDED


def test_forged_context_is_rejected_before_the_gate() -> None:
    seam = Seam()

    async def work() -> Any:
        context = seam.mint(value=disclosed())
        forged = replace(context, deadline=datetime(2027, 1, 1, tzinfo=NOW.tzinfo))
        return await seam.host.governed_chat(forged, chat())

    with pytest.raises(HostError) as error:
        seam.run(work)
    assert error.value.failure is HostFailure.FOREIGN_CONTEXT
    assert seam.model.chat_calls == 0


def test_declaration_is_immutable_and_bound_at_minting() -> None:
    value = disclosed(DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC})))
    with pytest.raises(FrozenInstanceError):
        value.declaration = ALL_REAL  # type: ignore[misc]
    with pytest.raises(FrozenInstanceError):
        value.declaration.classes = REAL  # type: ignore[misc]
    seam = Seam()
    context = seam.mint(value=value)
    minted = seam.host._minted[context.execution_id]  # type: ignore[attr-defined]
    assert minted[2] is value
    with pytest.raises(TypeError):
        seam.host.model_execution(ModelPurpose.CHAT, disclosure=ALL_REAL)  # type: ignore[arg-type]


def test_check_content_cannot_invent_a_repository_identity() -> None:
    seam = Seam()
    derived_elsewhere = DisclosureDeclaration(
        frozenset({DisclosureClass.DERIVED_DIAGNOSTIC}), OTHER_REPO
    )
    result = governed(
        seam,
        disclosed(derived_elsewhere),
        "ruff: repo-a/src/x.py:1 E501 repository repo-a",
    )
    refused(seam, result, DisclosureRefusal.REPOSITORY_NOT_ADMITTED)


# Evidence


def test_evidence_contains_only_safe_facts() -> None:
    seam = Seam()
    admitted = governed(seam, disclosed())
    other = Seam()
    rejected = governed(other, disclosed(consumer="other-app"))
    for owner, result in ((seam, admitted), (other, rejected)):
        record = owner.custody.read(
            EvidenceId(f"disclosure-{result.execution.execution_id.value}"),
            owner.tenant,
        )
        assert record is not None
        observation = record.subject
        assert type(observation) is DisclosureObservation
        names = set(observation.__slots__)
        assert not names & {
            "prompt",
            "content",
            "messages",
            "response",
            "credential",
            "authorization",
            "header",
            "api_key",
        }
        rendered = repr(record) + str(record) + repr(observation)
        for value in vars_of(observation):
            rendered += str(value)
        for canary in (PROMPT, REPLY, "CANARY", "def secret"):
            assert canary not in rendered, canary
    assert seam.observation(admitted.execution.execution_id.value).repository == REPO
    assert other.observation(rejected.execution.execution_id.value).refusal is (
        DisclosureRefusal.CONSUMER_MISMATCH
    )


def vars_of(value: object) -> list[object]:
    return [getattr(value, name) for name in value.__slots__]  # type: ignore[attr-defined]


def test_repository_recorded_only_when_applicable() -> None:
    seam = Seam()
    task = disclosed(DisclosureDeclaration(frozenset({DisclosureClass.TASK_TEXT})))
    result = governed(seam, task)
    assert seam.observation(result.execution.execution_id.value).repository is None


def test_refusal_evidence_custody_failure_still_settles_none() -> None:
    seam = Seam()
    seam.host._gate = replace(seam.host._gate, custody=FailingCustody())  # type: ignore[attr-defined]
    states: list[ExecutionState | None] = []

    async def work() -> Any:
        context = seam.mint(value=None)
        try:
            return await seam.host.governed_chat(context, chat())
        finally:
            coordinator = seam.host._coordinator  # type: ignore[attr-defined]
            states.append(await coordinator.current_state(context.execution_id))

    with pytest.raises(RuntimeError, match="custody unavailable"):
        seam.run(work)
    assert states == [ExecutionState.FAILED]
    assert seam.model.chat_calls == 0


def test_admitted_evidence_custody_failure_preserves_the_outcome() -> None:
    seam = Seam()
    seam.host._gate = replace(seam.host._gate, custody=FailingCustody())  # type: ignore[attr-defined]
    states: list[Any] = []

    async def work() -> Any:
        context = seam.mint(value=disclosed())
        try:
            return await seam.host.governed_chat(context, chat())
        finally:
            coordinator = seam.host._coordinator  # type: ignore[attr-defined]
            states.append(await coordinator.current_state(context.execution_id))

    with pytest.raises(RuntimeError, match="custody unavailable"):
        seam.run(work)
    assert states == [ExecutionState.SUCCEEDED]
    assert seam.model.chat_calls == 1


def test_admitted_preflight_failure_records_nothing_sent() -> None:
    model = RecordingModel()
    model.error = ModelPreflightError("connection refused")
    seam = Seam(model=model)
    result = governed(seam, disclosed())
    assert result.execution.effect is EffectExtent.NONE
    assert seam.observation(result.execution.execution_id.value).effect is (
        EffectExtent.NONE
    )


# Cancellation


def test_cancellation_inside_the_gate_never_reaches_the_provider() -> None:
    def cancelled() -> datetime:
        raise asyncio.CancelledError

    seam = Seam(gate={"clock": cancelled})
    with pytest.raises(asyncio.CancelledError):
        governed(seam, disclosed())
    assert seam.model.chat_calls == 0


def test_cancellation_during_an_admitted_call_is_attributed_unknown() -> None:
    model = RecordingModel()
    model.error = asyncio.CancelledError()  # type: ignore[assignment]
    seam = Seam(model=model)
    executions: list[Any] = []

    async def work() -> Any:
        context = seam.mint(value=disclosed())
        executions.append(context.execution_id.value)
        return await seam.host.governed_chat(context, chat())

    with pytest.raises(asyncio.CancelledError):
        seam.run(work)
    assert seam.observation(executions[0]).effect is EffectExtent.UNKNOWN


# LOCAL and REMOTE


def test_local_host_without_a_gate_ignores_declarations() -> None:
    model = FakeModel()
    config = configured(
        fake_binding(model), remote_binding(), disclosure_config=disclosure()
    )
    host = open_local_host(config, selection("fake"), clock=lambda: NOW)
    assert host._gate is None  # type: ignore[attr-defined]

    async def work() -> Any:
        return [
            await host.governed_chat(host.model_execution(ModelPurpose.CHAT), chat()),
            await host.governed_chat(
                host.model_execution(ModelPurpose.CHAT, disclosure=disclosed()), chat()
            ),
        ]

    results = asyncio.run(work())
    assert all(r.execution.final_state is ExecutionState.SUCCEEDED for r in results)
    assert model.chat_calls == 2


def test_remote_selection_is_still_refused_at_open() -> None:
    config = configured(remote_binding(), disclosure_config=disclosure())
    with pytest.raises(HostError) as error:
        open_local_host(config, selection("remote"), clock=lambda: NOW)
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION


def test_human_access_condition_respected() -> None:
    restricted = declaration(
        human_access=HumanAccessFact(HumanAccess.YES, DECLARED, SOURCE)
    )
    seam = Seam(disclosure_config=disclosure(declarations=(restricted,)))
    refused(seam, governed(seam, disclosed()), DisclosureRefusal.CONDITION_UNMET)
