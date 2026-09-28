"""ADR-014 CR-1b: the public local governed host, exercised through public imports.

Only `legoai.runtime.api`, `legoai.runtime.local` and owner values/Ports are
imported here. Transport is mocked; no provider service is contacted.
"""

import asyncio
import json
import socket
import threading
import urllib.request
from collections.abc import Callable, Mapping
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import TracebackType

import pytest

from legoai.execution.agent.ports import AgentDefinition, AgentRequest
from legoai.execution.agent.values import (
    AgentExecutionStatus,
    AgentId,
    AgentOutputContract,
)
from legoai.execution.ports import ExecutionTransitionError
from legoai.execution.values import ExecutionContext, ExecutionState
from legoai.governance.ports import AuthorizationOutcome
from legoai.governance.values import GrantId, PolicyRef
from legoai.intelligence.model.ports import (
    ModelPort,
    ModelPreflightError,
    ModelResponseRejectedError,
    ModelResponseUncertainError,
)
from legoai.intelligence.model.routing import ModelRequirement
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ChatRole,
    EmbeddingRequest,
    EmbeddingResult,
    ModelId,
    ProviderId,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.identity import ApplicationId, CorrelationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.plugins.values import PluginId
from legoai.runtime.api import (
    GovernedHost,
    HostError,
    HostFailure,
    LocalHostConfig,
    ModelBindingConfig,
    ModelPurpose,
    OllamaSettings,
    OperatorGrant,
    TrustedModelContribution,
)
from legoai.runtime.local import open_local_host

NOW = datetime(2026, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)
ACTIVE = (NOW, NOW + HOUR)
EXPIRED = (NOW - 2 * HOUR, NOW - HOUR)
FUTURE = (NOW + HOUR, NOW + 2 * HOUR)
PROFILE = ModelRequirement("assistant")
ALL = frozenset(ModelPurpose)
CHAT_ONLY = frozenset({ModelPurpose.CHAT})


def _target(tenant: str = "tenant-a", application: str = "app") -> ConfigurationRef:
    return ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", TenantId(tenant)), ApplicationId(application)
        ),
        "models",
    )


REVISION = ConfigurationRevisionRef(_target(), "r1", Version(1, 0, 0))


class FakeModel:
    """Trusted test ModelPort with invocation counters; performs no I/O."""

    def __init__(self, reply: str = "fake reply") -> None:
        self.reply = reply
        self.chat_calls = 0
        self.embed_calls = 0
        self.error: Exception | None = None

    async def chat(self, request: ChatRequest) -> ChatResult:
        self.chat_calls += 1
        if self.error is not None:
            raise self.error
        return ChatResult(self.reply, ModelId("fake-model"), ProviderId("fake"), None)

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResult:
        self.embed_calls += 1
        if self.error is not None:
            raise self.error
        vectors = tuple((1.0, 0.0) for _ in request.inputs)
        return EmbeddingResult(vectors, 2, ModelId("fake-embed"), ProviderId("fake"))


def grant(
    purpose: ModelPurpose = ModelPurpose.CHAT,
    window: tuple[datetime, datetime] = ACTIVE,
    *,
    grant_id: str | None = None,
) -> OperatorGrant:
    return OperatorGrant(
        GrantId(grant_id or f"grant-{purpose.value}"),
        "invoke-capability",
        purpose.capability_id.value,
        *window,
    )


def fake_binding(
    model: FakeModel,
    binding_id: str = "fake",
    purposes: frozenset[ModelPurpose] = ALL,
    *,
    constructions: list[str] | None = None,
) -> ModelBindingConfig:
    def construct() -> ModelPort:
        if constructions is not None:
            constructions.append(binding_id)
        return model

    return ModelBindingConfig(
        binding_id,
        PROFILE,
        TrustedModelContribution(
            PluginId("legoai.test", binding_id),
            ProviderId("fake"),
            ModelId("fake-model"),
            purposes,
            construct,
        ),
    )


def ollama_binding(binding_id: str = "ollama") -> ModelBindingConfig:
    return ModelBindingConfig(
        binding_id,
        PROFILE,
        OllamaSettings(
            "http://127.0.0.1:11434",
            "chat-model",
            "embed-model",
            5.0,
            ProviderId("ollama"),
        ),
    )


def host_config(
    *bindings: ModelBindingConfig,
    grants: tuple[OperatorGrant, ...] | None = None,
    max_executions: int = 8,
) -> LocalHostConfig:
    return LocalHostConfig(
        REVISION,
        PrincipalRef("operator", PrincipalId("service")),
        PolicyRef("operator", "policy", Version(1, 0, 0)),
        grants
        if grants is not None
        else (grant(ModelPurpose.CHAT), grant(ModelPurpose.EMBEDDING)),
        bindings,
        max_executions,
    )


def selection(binding: str = "fake", revision: str = "r1") -> dict[str, object]:
    return {"revision": revision, "binding": binding}


def open_fake(
    model: FakeModel | None = None,
    *,
    purposes: frozenset[ModelPurpose] = ALL,
    grants: tuple[OperatorGrant, ...] | None = None,
    max_executions: int = 8,
    clock: Callable[[], datetime] = lambda: NOW,
) -> tuple[GovernedHost, FakeModel]:
    model = model or FakeModel()
    config = host_config(
        fake_binding(model, purposes=purposes),
        grants=grants,
        max_executions=max_executions,
    )
    return open_local_host(config, selection(), clock=clock), model


def chat_request(text: str = "hello") -> ChatRequest:
    return ChatRequest((ChatMessage(ChatRole.USER, text),))


def failure(error: pytest.ExceptionInfo[HostError]) -> HostFailure:
    return error.value.failure


# --- A. Configuration validation -------------------------------------------


@pytest.mark.parametrize(
    "window",
    [
        (datetime(2026, 1, 1), NOW + HOUR),
        (NOW, datetime(2026, 1, 2)),
        (NOW, NOW),
        (NOW + HOUR, NOW),
    ],
    ids=["naive-start", "naive-end", "empty", "inverted"],
)
def test_grant_window_must_be_aware_and_ordered(
    window: tuple[datetime, datetime],
) -> None:
    with pytest.raises(HostError) as error:
        OperatorGrant(GrantId("g"), "invoke-capability", "scope", *window)
    assert failure(error) is HostFailure.INVALID_GRANT


@pytest.mark.parametrize("text", ["", " ", "a\nb", "x" * 257])
def test_grant_text_is_bounded(text: str) -> None:
    with pytest.raises(HostError) as error:
        OperatorGrant(GrantId("g"), text, "scope", *ACTIVE)
    assert failure(error) is HostFailure.INVALID_GRANT
    with pytest.raises(TypeError):
        OperatorGrant(GrantId("g"), 1, "scope", *ACTIVE)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", [0, 100_001])
def test_capacity_bounds(value: int) -> None:
    with pytest.raises(HostError) as error:
        host_config(fake_binding(FakeModel()), max_executions=value)
    assert failure(error) is HostFailure.INVALID_CONFIGURATION
    with pytest.raises(TypeError):
        host_config(fake_binding(FakeModel()), max_executions=True)


def test_grant_and_binding_counts_are_bounded() -> None:
    with pytest.raises(HostError) as error:
        host_config(fake_binding(FakeModel()), grants=())
    assert failure(error) is HostFailure.INVALID_CONFIGURATION
    many = tuple(fake_binding(FakeModel(), f"b{i}") for i in range(17))
    with pytest.raises(HostError) as error:
        host_config(*many)
    assert failure(error) is HostFailure.INVALID_CONFIGURATION


@pytest.mark.parametrize(
    "grants",
    [
        (grant(), grant(ModelPurpose.EMBEDDING, grant_id="grant-chat")),
        (grant(), grant(grant_id="other")),
    ],
    ids=["duplicate-id", "duplicate-action-scope"],
)
def test_duplicate_grants_conflict(grants: tuple[OperatorGrant, ...]) -> None:
    with pytest.raises(HostError) as error:
        host_config(fake_binding(FakeModel()), grants=grants)
    assert failure(error) is HostFailure.CONTRIBUTION_CONFLICT


def test_duplicate_binding_conflicts() -> None:
    with pytest.raises(HostError) as error:
        host_config(fake_binding(FakeModel()), fake_binding(FakeModel()))
    assert failure(error) is HostFailure.CONTRIBUTION_CONFLICT


@pytest.mark.parametrize(
    "extra",
    ["tenant", "grant", "class", "import", "module", "secret_ref", "constructor"],
)
def test_selection_data_is_closed(extra: str) -> None:
    config = host_config(fake_binding(FakeModel()))
    with pytest.raises(HostError) as error:
        open_local_host(config, {**selection(), extra: "x"}, clock=lambda: NOW)
    assert failure(error) is HostFailure.INVALID_CONFIGURATION


def test_selection_revision_and_binding_are_pinned() -> None:
    config = host_config(fake_binding(FakeModel()))
    with pytest.raises(HostError) as error:
        open_local_host(config, selection(revision="r0"), clock=lambda: NOW)
    assert failure(error) is HostFailure.STALE_CONFIGURATION
    with pytest.raises(HostError) as error:
        open_local_host(config, selection("unknown"), clock=lambda: NOW)
    assert failure(error) is HostFailure.UNKNOWN_BINDING
    with pytest.raises(TypeError):
        open_local_host(config, [("revision", "r1")], clock=lambda: NOW)  # type: ignore[arg-type]


def test_contribution_purposes_are_closed_and_chat_anchored() -> None:
    with pytest.raises(HostError) as error:
        fake_binding(FakeModel(), purposes=frozenset())
    assert failure(error) is HostFailure.INVALID_CONFIGURATION
    with pytest.raises(TypeError):
        fake_binding(FakeModel(), purposes=frozenset({"chat"}))  # type: ignore[arg-type]
    config = host_config(
        fake_binding(FakeModel(), purposes=frozenset({ModelPurpose.EMBEDDING}))
    )
    with pytest.raises(HostError) as error:
        open_local_host(config, selection(), clock=lambda: NOW)
    assert failure(error) is HostFailure.UNSUPPORTED_COMPOSITION


def test_invalid_builtin_settings_fail_at_open() -> None:
    binding = ModelBindingConfig(
        "ollama",
        PROFILE,
        OllamaSettings("ftp://user:pw@host", "m", "e", 5.0, ProviderId("ollama")),
    )
    with pytest.raises(HostError) as error:
        open_local_host(host_config(binding), selection("ollama"), clock=lambda: NOW)
    assert failure(error) is HostFailure.INVALID_CONFIGURATION


# --- B. Open behavior --------------------------------------------------------


def _deny(*args: object, **kwargs: object) -> object:
    raise AssertionError("provider, network or thread activity during open")


def test_open_is_inert_and_constructs_only_selected_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    constructions: list[str] = []
    model = FakeModel()
    config = host_config(
        fake_binding(model, constructions=constructions),
        fake_binding(FakeModel(), "unselected", constructions=constructions),
        ollama_binding(),
    )
    threads = threading.active_count()
    monkeypatch.setattr(urllib.request, "urlopen", _deny)
    monkeypatch.setattr(socket.socket, "connect", _deny)
    monkeypatch.setattr(threading.Thread, "start", _deny)
    host = open_local_host(config, selection(), clock=lambda: NOW)
    assert constructions == ["fake"]
    assert threading.active_count() == threads
    assert list(tmp_path.iterdir()) == []
    assert model.chat_calls == model.embed_calls == 0
    host.model_execution(ModelPurpose.CHAT)
    assert constructions == ["fake"]


def test_builtin_ollama_open_makes_no_request(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _deny)
    monkeypatch.setattr(socket.socket, "connect", _deny)
    host = open_local_host(
        host_config(ollama_binding()), selection("ollama"), clock=lambda: NOW
    )
    assert host.model_execution(ModelPurpose.EMBEDDING) is not None


@pytest.mark.parametrize(
    ("raised", "expected"),
    [
        (ImportError("missing"), HostFailure.MISSING_DEPENDENCY),
        (RuntimeError("broken"), HostFailure.INITIALIZATION_FAILURE),
    ],
)
def test_constructor_failure_returns_no_host(
    raised: Exception, expected: HostFailure
) -> None:
    def construct() -> ModelPort:
        raise raised

    binding = ModelBindingConfig(
        "fake",
        PROFILE,
        TrustedModelContribution(
            PluginId("legoai.test", "broken"),
            ProviderId("fake"),
            ModelId("fake-model"),
            ALL,
            construct,
        ),
    )
    with pytest.raises(HostError) as error:
        open_local_host(host_config(binding), selection(), clock=lambda: NOW)
    assert failure(error) is expected
    assert error.value.__cause__ is not None
    assert str(error.value) == expected.value


def test_constructor_must_supply_model_port() -> None:
    binding = ModelBindingConfig(
        "fake",
        PROFILE,
        TrustedModelContribution(
            PluginId("legoai.test", "not-a-port"),
            ProviderId("fake"),
            ModelId("fake-model"),
            ALL,
            object,  # type: ignore[arg-type]
        ),
    )
    with pytest.raises(HostError) as error:
        open_local_host(host_config(binding), selection(), clock=lambda: NOW)
    assert failure(error) is HostFailure.INITIALIZATION_FAILURE


# --- C. Provider/config substitution ----------------------------------------


class _Response:
    def __init__(self, body: Mapping[str, object]) -> None:
        self._body = json.dumps(body).encode("utf-8")
        self.status = 200

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _Response:
        return self

    def __exit__(
        self,
        kind: type[BaseException] | None,
        value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        return None


def _ollama(request: urllib.request.Request, timeout: float | None = None) -> _Response:
    assert isinstance(request.data, bytes)
    body = json.loads(request.data)
    if request.full_url.endswith("/api/chat"):
        return _Response({"message": {"content": "ollama reply"}})
    return _Response({"embeddings": [[0.5, 0.5] for _ in body["input"]]})


async def consumer(host: GovernedHost) -> tuple[str, int]:
    """Application domain code: public contracts only, provider-agnostic."""
    chat = await host.governed_chat(
        host.model_execution(ModelPurpose.CHAT), chat_request()
    )
    embed = await host.governed_embed(
        host.model_execution(ModelPurpose.EMBEDDING), EmbeddingRequest(("a", "b"))
    )
    assert chat.response is not None and embed.response is not None
    return chat.response.content, len(embed.response.vectors)


@pytest.mark.parametrize(
    ("binding", "reply"), [("fake", "fake reply"), ("ollama", "ollama reply")]
)
def test_same_consumer_code_under_changed_selection(
    binding: str, reply: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _ollama)
    config = host_config(fake_binding(FakeModel()), ollama_binding())
    host = open_local_host(config, selection(binding), clock=lambda: NOW)
    assert asyncio.run(consumer(host)) == (reply, 2)


# --- D. Authority ------------------------------------------------------------


def test_missing_grant_fails_before_registration() -> None:
    host, model = open_fake(grants=(grant(ModelPurpose.EMBEDDING),))
    with pytest.raises(HostError) as error:
        host.model_execution(ModelPurpose.CHAT)
    assert failure(error) is HostFailure.GRANT_NOT_CONFIGURED
    assert model.chat_calls == 0


@pytest.mark.parametrize("window", [EXPIRED, FUTURE], ids=["expired", "not-yet-valid"])
def test_configured_but_invalid_grant_is_denied_before_provider(
    window: tuple[datetime, datetime],
) -> None:
    host, model = open_fake(grants=(grant(window=window),))
    context = host.model_execution(ModelPurpose.CHAT)
    result = asyncio.run(host.governed_chat(context, chat_request()))
    assert result.response is None
    assert result.execution.final_state is ExecutionState.REJECTED
    assert result.execution.effect is EffectExtent.NONE
    assert model.chat_calls == 0


def test_authorization_is_current_at_dispatch_not_at_minting() -> None:
    times = [NOW]
    host, model = open_fake(clock=lambda: times[-1])
    context = host.model_execution(ModelPurpose.CHAT)
    times.append(NOW + 2 * HOUR)  # the grant expired after minting
    result = asyncio.run(host.governed_chat(context, chat_request()))
    assert result.execution.final_state is ExecutionState.REJECTED
    assert model.chat_calls == 0


def test_security_context_selects_only_exact_configured_grants() -> None:
    read = OperatorGrant(
        GrantId("read"), "read-for-model-analysis", "workspace", *ACTIVE
    )
    stale = OperatorGrant(GrantId("stale"), "read-stale", "workspace", *EXPIRED)
    host, _ = open_fake(grants=(grant(), read, stale))
    workspace = replace(REVISION.configuration, instance="workspace")
    context = host.security_context(workspace, "read-for-model-analysis", "workspace")
    assert context.operation.subject == workspace and context.approval is None
    decision = host.authorization.evaluate(context)
    assert decision.outcome is AuthorizationOutcome.ALLOWED
    expired = host.security_context(workspace, "read-stale", "workspace")
    assert host.authorization.evaluate(expired).outcome is AuthorizationOutcome.DENIED
    for action, scope in (("read-for-model-analysis", "other"), ("admin", "workspace")):
        with pytest.raises(HostError) as error:
            host.security_context(workspace, action, scope)
        assert failure(error) is HostFailure.GRANT_NOT_CONFIGURED


@pytest.mark.parametrize(
    "subject",
    [_target(application="other"), _target(tenant="tenant-b")],
    ids=["other-application", "other-tenant"],
)
def test_security_context_subject_scope(subject: ConfigurationRef) -> None:
    host, _ = open_fake()
    with pytest.raises(HostError) as error:
        host.security_context(
            subject, "invoke-capability", "legoai.intelligence.model.chat"
        )
    assert failure(error) is HostFailure.SUBJECT_OUT_OF_SCOPE


def test_model_output_cannot_manufacture_authority() -> None:
    forged = json.dumps(
        {"grant": {"action": "admin", "resource_scope": "*"}, "tenant": "tenant-b"}
    )
    host, model = open_fake(FakeModel(forged))
    context = host.model_execution(ModelPurpose.CHAT)
    result = asyncio.run(host.governed_chat(context, chat_request()))
    assert result.response is not None and result.response.content == forged
    with pytest.raises(HostError) as error:
        host.security_context(REVISION.configuration, "admin", "*")
    assert failure(error) is HostFailure.GRANT_NOT_CONFIGURED


# --- E. Context ownership -----------------------------------------------------


def test_foreign_and_wrong_purpose_contexts_are_refused() -> None:
    host, model = open_fake()
    other, _ = open_fake()
    foreign = other.model_execution(ModelPurpose.CHAT)
    chat = host.model_execution(ModelPurpose.CHAT)
    embed = host.model_execution(ModelPurpose.EMBEDDING)
    tampered = replace(chat, correlation_id=CorrelationId("forged"))

    async def attempts() -> list[HostFailure]:
        failures: list[HostFailure] = []
        for context in (foreign, tampered, embed):
            try:
                await host.governed_chat(context, chat_request())
            except HostError as error:
                failures.append(error.failure)
        try:
            await host.governed_embed(chat, EmbeddingRequest(("a",)))
        except HostError as error:
            failures.append(error.failure)
        return failures

    assert asyncio.run(attempts()) == [HostFailure.FOREIGN_CONTEXT] * 4
    assert model.chat_calls == model.embed_calls == 0


# --- F. Capacity --------------------------------------------------------------


def test_capacity_is_a_hard_lifetime_bound_without_release() -> None:
    host, model = open_fake(max_executions=2)
    first = host.model_execution(ModelPurpose.CHAT)
    with pytest.raises(ValueError):
        host.model_execution(ModelPurpose.CHAT, deadline=datetime(2026, 1, 1))
    second = host.model_execution(ModelPurpose.EMBEDDING)
    with pytest.raises(HostError) as error:
        host.model_execution(ModelPurpose.CHAT)
    assert failure(error) is HostFailure.CAPACITY_EXHAUSTED

    async def use() -> None:
        # Already minted work is unaffected by exhaustion.
        assert (await host.governed_chat(first, chat_request())).response is not None
        assert (await host.governed_embed(second, EmbeddingRequest(("a",)))).response
        # No release: a finished execution cannot be invoked again.
        with pytest.raises(ExecutionTransitionError):
            await host.governed_chat(first, chat_request())

    asyncio.run(use())
    assert model.chat_calls == 1 and model.embed_calls == 1
    with pytest.raises(HostError) as error:
        host.model_execution(ModelPurpose.CHAT)
    assert failure(error) is HostFailure.CAPACITY_EXHAUSTED


def test_rejected_allocations_do_not_consume_capacity() -> None:
    host, _ = open_fake(
        purposes=CHAT_ONLY, grants=(grant(ModelPurpose.CHAT),), max_executions=1
    )
    with pytest.raises(HostError) as error:
        host.model_execution(ModelPurpose.EMBEDDING)
    assert failure(error) is HostFailure.PURPOSE_UNAVAILABLE
    with pytest.raises(TypeError):
        host.model_execution(ModelPurpose.CHAT, correlation="c")  # type: ignore[arg-type]
    assert host.model_execution(ModelPurpose.CHAT) is not None


# --- G. Event-loop / thread confinement ---------------------------------------


def test_same_loop_use_and_cross_loop_refusal() -> None:
    host, model = open_fake()

    async def twice() -> None:
        for _ in range(2):
            context = host.model_execution(ModelPurpose.CHAT)
            assert (await host.governed_chat(context, chat_request())).response

    asyncio.run(twice())
    context = host.model_execution(ModelPurpose.CHAT)
    with pytest.raises(HostError) as error:
        asyncio.run(host.governed_chat(context, chat_request()))
    assert failure(error) is HostFailure.WRONG_EVENT_LOOP
    assert model.chat_calls == 2


def test_other_thread_is_refused() -> None:
    host, _ = open_fake()
    failures: list[HostFailure] = []

    def worker() -> None:
        try:
            host.model_execution(ModelPurpose.CHAT)
        except HostError as error:
            failures.append(error.failure)

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    assert failures == [HostFailure.WRONG_EVENT_LOOP]


# --- H. Chat -------------------------------------------------------------------


def test_chat_success_uses_existing_semantics() -> None:
    host, model = open_fake()
    context = host.model_execution(ModelPurpose.CHAT)
    result = asyncio.run(host.governed_chat(context, chat_request()))
    assert result.execution.execution_id == context.execution_id
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert result.execution.effect is EffectExtent.COMPLETED
    assert result.response is not None and result.response.content == "fake reply"
    assert model.chat_calls == 1


@pytest.mark.parametrize(
    ("raised", "effect"),
    [
        (ModelPreflightError("refused"), EffectExtent.NONE),
        (ModelResponseRejectedError("rejected"), EffectExtent.NONE),
        (ModelResponseUncertainError("lost"), EffectExtent.UNKNOWN),
    ],
    ids=["preflight", "rejected", "uncertain"],
)
def test_chat_failures_keep_effect_mapping_without_retry(
    raised: Exception, effect: EffectExtent
) -> None:
    host, model = open_fake()
    model.error = raised
    context = host.model_execution(ModelPurpose.CHAT)
    result = asyncio.run(host.governed_chat(context, chat_request()))
    assert result.response is None
    assert result.execution.final_state is ExecutionState.FAILED
    assert result.execution.effect is effect
    assert model.chat_calls == 1


def test_elapsed_deadline_rejects_before_provider() -> None:
    host, model = open_fake()
    context = host.model_execution(ModelPurpose.CHAT, deadline=NOW - HOUR)
    result = asyncio.run(host.governed_chat(context, chat_request()))
    assert result.execution.final_state is ExecutionState.REJECTED
    assert model.chat_calls == 0


# --- I. Embedding ----------------------------------------------------------------


def test_embedding_uses_the_same_selected_binding() -> None:
    host, model = open_fake()

    async def both() -> None:
        await host.governed_chat(
            host.model_execution(ModelPurpose.CHAT), chat_request()
        )
        result = await host.governed_embed(
            host.model_execution(ModelPurpose.EMBEDDING), EmbeddingRequest(("a",))
        )
        assert result.execution.effect is EffectExtent.COMPLETED
        assert result.response is not None and result.response.dimension == 2

    asyncio.run(both())
    assert model.chat_calls == 1 and model.embed_calls == 1


def test_embedding_unavailable_has_no_fallback() -> None:
    constructions: list[str] = []
    config = host_config(
        fake_binding(FakeModel(), purposes=CHAT_ONLY, constructions=constructions),
        fake_binding(FakeModel(), "embedder", constructions=constructions),
    )
    host = open_local_host(config, selection(), clock=lambda: NOW)
    with pytest.raises(HostError) as error:
        host.model_execution(ModelPurpose.EMBEDDING)
    assert failure(error) is HostFailure.PURPOSE_UNAVAILABLE
    assert constructions == ["fake"]


def test_embedding_uncertainty_is_unknown() -> None:
    host, model = open_fake()
    model.error = ModelResponseUncertainError("lost")
    context = host.model_execution(ModelPurpose.EMBEDDING)
    result = asyncio.run(host.governed_embed(context, EmbeddingRequest(("a",))))
    assert result.execution.effect is EffectExtent.UNKNOWN
    assert model.embed_calls == 1


def test_builtin_embedding_through_mocked_transport(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(urllib.request, "urlopen", _ollama)
    host = open_local_host(
        host_config(ollama_binding()), selection("ollama"), clock=lambda: NOW
    )
    context = host.model_execution(ModelPurpose.EMBEDDING)
    result = asyncio.run(host.governed_embed(context, EmbeddingRequest(("a",))))
    assert result.response is not None
    assert result.response.model_identity == ModelId("embed-model")


# --- J. Agent runtime ---------------------------------------------------------------


def definition(profile: str = "assistant") -> AgentDefinition:
    return AgentDefinition(
        AgentId("assistant"),
        Version(1, 0, 0),
        "Answer briefly.",
        ModelRequirement(profile),
        AgentOutputContract(64),
        128,
        512,
    )


def test_agent_runtime_public_path_calls_model_once() -> None:
    host, model = open_fake()
    context = host.model_execution(ModelPurpose.CHAT)
    result = asyncio.run(
        host.agent_runtime().run(definition(), AgentRequest(context, "question"))
    )
    assert result.status is AgentExecutionStatus.SUCCEEDED
    assert result.execution_id == context.execution_id
    assert result.output == "fake reply" and model.chat_calls == 1


def test_agent_routing_miss_and_uncertainty() -> None:
    host, model = open_fake()
    miss = asyncio.run(
        host.agent_runtime().run(
            definition("other"),
            AgentRequest(host.model_execution(ModelPurpose.CHAT), "q"),
        )
    )
    assert miss.status is AgentExecutionStatus.ROUTING_FAILED and model.chat_calls == 0
    host, model = open_fake()
    model.error = ModelResponseUncertainError("lost")
    lost = asyncio.run(
        host.agent_runtime().run(
            definition(), AgentRequest(host.model_execution(ModelPurpose.CHAT), "q")
        )
    )
    assert lost.status is AgentExecutionStatus.MODEL_FAILED
    assert lost.model_execution is not None
    assert lost.model_execution.effect is EffectExtent.UNKNOWN
    assert model.chat_calls == 1


def test_agent_refuses_foreign_context() -> None:
    host, model = open_fake()
    other, _ = open_fake()
    foreign: ExecutionContext = other.model_execution(ModelPurpose.CHAT)
    with pytest.raises(HostError) as error:
        asyncio.run(host.agent_runtime().run(definition(), AgentRequest(foreign, "q")))
    assert failure(error) is HostFailure.FOREIGN_CONTEXT
    assert model.chat_calls == 0


# --- K. Host isolation ----------------------------------------------------------------


def test_two_hosts_share_no_state() -> None:
    first, first_model = open_fake(max_executions=1)
    second, second_model = open_fake(purposes=CHAT_ONLY, max_executions=1)
    first_context = first.model_execution(ModelPurpose.EMBEDDING)
    second_context = second.model_execution(ModelPurpose.CHAT)
    assert first_context.execution_id != second_context.execution_id
    with pytest.raises(HostError) as error:
        second.model_execution(ModelPurpose.EMBEDDING)
    assert failure(error) is HostFailure.PURPOSE_UNAVAILABLE
    assert first.authorization is not second.authorization
    with pytest.raises(HostError) as error:
        asyncio.run(second.governed_chat(first_context, chat_request()))
    assert failure(error) is HostFailure.FOREIGN_CONTEXT
    assert first_model.embed_calls == second_model.chat_calls == 0
