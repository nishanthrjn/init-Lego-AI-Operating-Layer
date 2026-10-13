"""OPENAI-COMPATIBLE-REMOTE-1 through the PUBLIC governed host.

`open_local_host(..., remote=RemoteModelRuntime(...))` with a credentialed
REMOTE `OpenAICompatibleSettings`, remote-disclosure configuration, an S1
credential and owner-local custody; every invocation goes GovernedHost ->
governed chat/embed -> disclosure gate -> INTENDED -> per-invocation Secret
use -> T2 -> a process-local synthetic TLS server emulating the
OpenAI-compatible contract -> the shared adapter parser -> governed result.

Synthetic canaries only: no external network, provider, KISSKI or real key.
Private reach-ins are limited to inspection, the S1 test bootstrap seam and
fault injection; every proof of behavior uses the public invocation path.
"""

import asyncio
import json
import logging
import socket
import sqlite3
import threading
from collections.abc import Awaitable, Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from legoai.evidence.custody import CustodyAccess
from legoai.evidence.ports import EvidenceId
from legoai.execution.agent.ports import AgentRequest
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.execution.values import ExecutionId, ExecutionState
from legoai.governance.disclosure import (
    DisclosureClass,
    DisclosureDeclaration,
    DisclosureObservation,
    DisclosureRefusal,
)
from legoai.governance.secret import (
    SecretRef,
    SecretRevisionRef,
    UseRecoveryCategory,
)
from legoai.governance.values import GrantId, PolicyRef, Principal
from legoai.intelligence.model.values import (
    ChatMessage,
    ChatRequest,
    ChatRole,
    EmbeddingRequest,
    ModelId,
    ProviderId,
)
from legoai.kernel.effects import EffectExtent
from legoai.kernel.errors import ErrorCategory, Recoverability
from legoai.kernel.identity import PrincipalId, TenantId
from legoai.kernel.references import PrincipalRef, ReferenceScope
from legoai.kernel.versions import Version
from legoai.reference._credential_https import _CredentialFlight
from legoai.reference._custody_sqlite import _StorageGap
from legoai.reference._remote_attempts import _RemoteAttemptStore
from legoai.reference._secret_ledger import _inspect_source
from legoai.reference.secret import _ProvisionedSecretSource
from legoai.runtime._composition.remote_model import (
    _Invocation,
    credential_consumer,
    credential_purpose,
)
from legoai.runtime._composition.secret import _provision_interactively
from legoai.runtime.api import (
    ExecutionDisclosure,
    GovernedHost,
    HostError,
    HostFailure,
    LocalHostConfig,
    ModelBindingConfig,
    ModelDeployment,
    ModelPurpose,
    OpenAICompatibleSettings,
    OperatorGrant,
    RemoteDisclosureConfig,
    RemoteModelRuntime,
)
from legoai.runtime.local import (
    _remote_chat_http_status,
    open_credential_source,
    open_local_host,
)
from tests.integration.composition.test_local_host import PROFILE, REVISION, definition
from tests.support.tls_server import TEST_CA, TlsServer
from tests.unit.governance.test_disclosure import (
    DAY,
    OTHER_REPO,
    admission,
    declaration,
)
from tests.unit.governance.test_disclosure import NOW as AT

CANARY = "remote-key-CANARY-DO-NOT-LEAK-662917"
PROMPT = "PROMPT-CANARY-5521 synthetic task text"
REPLY = "REPLY-CANARY-7713"
HOUR = timedelta(hours=1)
SCOPE = ReferenceScope("operator", TenantId("tenant-a"))
PRINCIPAL = PrincipalRef("operator", PrincipalId("service"))
CHAT_PATH = "/v1/chat/completions"
EMBED_PATH = "/v1/embeddings"
SYNTHETIC = ExecutionDisclosure(
    "forgeai", DisclosureDeclaration(frozenset({DisclosureClass.SYNTHETIC}))
)


def chat_body(
    *, model: str = "model-a", content: str = REPLY, finish: str = "stop"
) -> bytes:
    return json.dumps(
        {
            "id": "chatcmpl-synthetic",
            "object": "chat.completion",
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": content},
                    "finish_reason": finish,
                }
            ],
            "usage": {"prompt_tokens": 3, "completion_tokens": 2},
        }
    ).encode()


def embed_body(*, model: str = "embed-a", count: int = 1) -> bytes:
    return json.dumps(
        {
            "object": "list",
            "model": model,
            "data": [
                {"object": "embedding", "index": i, "embedding": [0.5, 0.25]}
                for i in range(count)
            ],
        }
    ).encode()


RESPONSES = {CHAT_PATH: chat_body(), EMBED_PATH: embed_body()}


class Clock:
    """The host's one trusted clock; tests move it explicitly."""

    def __init__(self) -> None:
        self.now = AT

    def __call__(self) -> datetime:
        return self.now


def server(mode: str = "ok", **options: Any) -> TlsServer:
    options.setdefault("responses", RESPONSES)
    return TlsServer(mode, expected=CANARY, **options)


class Remote:
    """One public REMOTE configuration against a synthetic TLS endpoint."""

    def __init__(
        self,
        directory: Path,
        port: int,
        *,
        embedding: bool = True,
        admission_changes: dict[str, Any] | None = None,
        settings_changes: dict[str, Any] | None = None,
        purpose: str | None = None,
        consumer: str | None = None,
        secret_window: tuple[datetime, datetime] = (AT - HOUR, AT + 3 * DAY),
        margin: timedelta = timedelta(minutes=5),
        timeout: float = 5.0,
    ) -> None:
        self.directory = directory
        self.clock = Clock()
        self.source = open_credential_source(SCOPE)
        self.credential = self.provision(purpose=purpose, consumer=consumer)
        self.origin = f"https://localhost:{port}"
        served = {"model-a", "embed-a"} if embedding else {"model-a"}
        purposes = {"chat", "embedding"} if embedding else {"chat"}
        changes: dict[str, Any] = {
            "endpoint_origin": self.origin,
            "models": frozenset(served),
            "purposes": frozenset(purposes),
        }
        self.admission = admission(**(changes | (admission_changes or {})))
        settings = OpenAICompatibleSettings(
            self.origin + "/v1",
            "model-a",
            "embed-a" if embedding else None,
            timeout,
            None,
            ProviderId("remote-endpoint"),
            ModelDeployment.REMOTE,
            bearer_credential=self.credential,
        )
        self.settings = replace(settings, **(settings_changes or {}))
        window = (AT - HOUR, AT + 3 * DAY)
        self.grants: tuple[OperatorGrant, ...] = (
            OperatorGrant(
                GrantId("grant-chat"),
                "invoke-capability",
                ModelPurpose.CHAT.capability_id.value,
                *window,
            ),
            OperatorGrant(
                GrantId("grant-embedding"),
                "invoke-capability",
                ModelPurpose.EMBEDDING.capability_id.value,
                *window,
            ),
            OperatorGrant(
                GrantId("grant-secret"),
                "secret-use",
                self.credential.exact.identity,
                *secret_window,
            ),
        )
        self.margin = margin
        self.host: Any = None

    def provision(
        self,
        *,
        purpose: str | None = None,
        consumer: str | None = None,
        identity: str = "remote-key",
    ) -> SecretRef:
        # S1's trusted test bootstrap seam: synthetic material, no terminal.
        return _provision_interactively(
            self.source._source,  # type: ignore[attr-defined]
            identity,
            purpose or credential_purpose(),
            consumer or credential_consumer(),
            read=lambda _: CANARY,
            interactive=lambda: True,
        )

    def config(self, **changes: Any) -> LocalHostConfig:
        value = LocalHostConfig(
            REVISION,
            PRINCIPAL,
            PolicyRef("operator", "policy", Version(1, 0, 0)),
            self.grants,
            (ModelBindingConfig("remote", PROFILE, self.settings),),
            64,
            disclosure=RemoteDisclosureConfig((self.declaration(),), (self.admission,)),
        )
        return replace(value, **changes)

    def declaration(self) -> Any:
        return declaration(endpoint_origin=self.origin)

    def runtime(self, **changes: Any) -> RemoteModelRuntime:
        value = RemoteModelRuntime(
            self.source, self.directory, self.margin, trust_anchor=TEST_CA
        )
        return replace(value, **changes)

    def open(self, **config_changes: Any) -> GovernedHost:
        host = self.host = open_local_host(
            self.config(**config_changes),
            {"revision": "r1", "binding": "remote"},
            clock=self.clock,
            remote=self.runtime(),
        )
        return host

    # Public invocations (one event loop per host)

    async def chat(
        self, text: str = PROMPT, disclosure: ExecutionDisclosure | None = SYNTHETIC
    ) -> Any:
        context = self.host.model_execution(ModelPurpose.CHAT, disclosure=disclosure)
        return await self.host.governed_chat(
            context, ChatRequest((ChatMessage(ChatRole.USER, text),))
        )

    async def embed(
        self,
        inputs: tuple[str, ...] = ("embed-me",),
        disclosure: ExecutionDisclosure | None = SYNTHETIC,
    ) -> Any:
        context = self.host.model_execution(
            ModelPurpose.EMBEDDING, disclosure=disclosure
        )
        return await self.host.governed_embed(context, EmbeddingRequest(inputs))

    # Inspection only

    def attempts(self) -> list[dict[str, Any]]:
        path = self.directory / "remote-attempts.db"
        if not path.exists():
            return []
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True)
        try:
            rows = conn.execute(
                "SELECT attempt_id,state,observations,record FROM attempts ORDER BY rowid"
            ).fetchall()
        finally:
            conn.close()
        return [
            {
                "id": key,
                "state": state,
                "observations": set(json.loads(observed)),
                "record": json.loads(record),
            }
            for key, state, observed, record in rows
        ]

    def uses(self) -> list[Any]:
        (ledger,) = self.directory.glob("secret-uses-*/source.db")
        statuses = _inspect_source(ledger, CustodyAccess(SCOPE, Principal(PRINCIPAL)))
        assert isinstance(statuses, tuple)
        return list(statuses)

    def observation(self, result: Any) -> DisclosureObservation:
        record = self.host._gate.custody.read(
            EvidenceId(f"disclosure-{result.execution.execution_id.value}"),
            self.host._tenant,
        )
        assert record is not None and type(record.subject) is DisclosureObservation
        return record.subject


def run(work: Callable[[], Awaitable[Any]]) -> Any:
    return asyncio.run(work())


def failed(
    result: Any,
    effect: EffectExtent,
    category: ErrorCategory,
    recoverability: Recoverability,
) -> None:
    execution = result.execution
    assert result.response is None
    assert execution.final_state is ExecutionState.FAILED
    assert execution.effect is effect
    assert execution.error is not None
    assert execution.error.category is category
    assert execution.error.recoverability is recoverability


def not_sent(result: Any) -> None:
    failed(
        result,
        EffectExtent.NONE,
        ErrorCategory.DEPENDENCY_FAILURE,
        Recoverability.POTENTIALLY_RETRYABLE,
    )


def leak_free(directory: Path, *values: object, log: str = "") -> None:
    for file in directory.rglob("*"):
        if file.is_file():
            data = file.read_bytes()
            assert CANARY.encode() not in data, file
            assert b"PROMPT-CANARY" not in data, file
            assert b"REPLY-CANARY" not in data, file
    for value in values:
        text = repr(value) + str(value)
        assert CANARY not in text and "Bearer" not in text, text
        assert "PROMPT-CANARY" not in text
    assert CANARY not in log and "PROMPT-CANARY" not in log


# --- Public end-to-end: chat and embedding ----------------------------------


def test_public_remote_chat_end_to_end(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with server() as tls:
        remote = Remote(tmp_path, tls.port, settings_changes={"max_output_tokens": 7})
        remote.open()
        result = run(remote.chat)
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert result.execution.effect is EffectExtent.COMPLETED
    assert result.response.content == REPLY
    assert result.response.model_identity == ModelId("model-a")
    assert result.response.provider_identity == ProviderId("remote-endpoint")
    # Exactly one verified request carrying exactly the provisioned credential.
    assert tls.connections == 1 and tls.requests == 1
    assert tls.authorized == [True]
    assert tls.paths == [f"POST {CHAT_PATH}"]
    assert tls.header_lines == [6]
    assert json.loads(tls.bodies[0]) == {
        "model": "model-a",
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": False,
        "max_tokens": 7,
    }
    (attempt,) = remote.attempts()
    assert attempt["state"] == "completed"
    assert attempt["observations"] == {"sent_all", "response_complete"}
    assert attempt["record"]["model"] == "model-a"
    assert attempt["record"]["binding_id"] == "remote"
    assert attempt["record"]["endpoint_origin"] == remote.origin
    assert attempt["record"]["execution_id"] == result.execution.execution_id.value
    (use,) = remote.uses()
    assert use.use_id.value == attempt["id"]  # the use IS this attempt's
    assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
    observation = remote.observation(result)
    assert observation.refusal is None and observation.effect is EffectExtent.COMPLETED
    assert observation.model == "model-a"
    leak_free(
        tmp_path,
        result,
        result.execution,
        remote.host,
        remote.settings,
        remote.config(),
        remote.runtime(),
        remote.source,
        observation,
        log=caplog.text,
    )


def test_public_remote_embedding_success_and_identity(tmp_path: Path) -> None:
    responses = {EMBED_PATH: embed_body(count=2)}
    with server(responses=responses) as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        result = run(lambda: remote.embed(("alpha", "beta")))
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert result.execution.effect is EffectExtent.COMPLETED
    assert result.response.vectors == ((0.5, 0.25), (0.5, 0.25))
    assert result.response.model_identity == ModelId("embed-a")
    assert tls.authorized == [True]
    assert json.loads(tls.bodies[0]) == {"model": "embed-a", "input": ["alpha", "beta"]}
    (attempt,) = remote.attempts()
    assert attempt["state"] == "completed"
    # The exact model of THIS purpose is bound into disclosure and attempt.
    assert attempt["record"]["model"] == "embed-a"
    assert attempt["record"]["capability"] == ModelPurpose.EMBEDDING.capability_id.value
    assert remote.observation(result).model == "embed-a"
    (use,) = remote.uses()
    assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED


def test_embedding_unavailable_without_embedding_model(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port, embedding=False)
        host = remote.open()
        with pytest.raises(HostError) as error:
            host.model_execution(ModelPurpose.EMBEDDING, disclosure=SYNTHETIC)
    assert error.value.failure is HostFailure.PURPOSE_UNAVAILABLE
    assert tls.connections == 0 and remote.attempts() == []


def test_chat_status_is_execution_scoped_ephemeral_and_not_embedding(
    tmp_path: Path,
) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        host = remote.open()
        assert _remote_chat_http_status(host, ExecutionId("not-this-execution")) is None

        async def work() -> Any:
            first = await remote.chat(text="synthetic")
            tls.mode = "403"
            tls.responses[CHAT_PATH] = CANARY.encode()
            second = await remote.chat(text="synthetic")
            embedded = await remote.embed()
            return first, second, embedded

        first, second, embedded = run(work)
        assert _remote_chat_http_status(host, first.execution.execution_id) == 200
        assert _remote_chat_http_status(host, second.execution.execution_id) == 403
        assert _remote_chat_http_status(host, embedded.execution.execution_id) is None
        assert first.execution.effect is EffectExtent.COMPLETED
        assert second.execution.effect is EffectExtent.NONE
        assert tls.requests == 3
    # Historical custody remains category-only: no status column or payload field.
    conn = sqlite3.connect(tmp_path / "remote-attempts.db")
    try:
        assert "provider_status" not in {
            row[1] for row in conn.execute("PRAGMA table_info(attempts)")
        }
    finally:
        conn.close()
    assert all("provider_status" not in row["record"] for row in remote.attempts())
    leak_free(tmp_path, second, remote.attempts())


def test_chat_status_absent_on_connection_failure(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        with patch("socket.getaddrinfo", side_effect=OSError("synthetic DNS failure")):
            result = run(remote.chat)
        assert tls.requests == 0
    not_sent(result)
    assert _remote_chat_http_status(remote.host, result.execution.execution_id) is None
    assert [row["state"] for row in remote.attempts()] == ["not_sent"]


@pytest.mark.parametrize("code", [401, 403, 404, 405, 429, 500, 503, 418])
def test_agent_rejection_keeps_only_safe_ephemeral_status(
    tmp_path: Path, code: int, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    with server(str(code), responses={CHAT_PATH: CANARY.encode()}) as tls:
        remote = Remote(tmp_path, tls.port)
        host = remote.open()
        context = host.model_execution(ModelPurpose.CHAT, disclosure=SYNTHETIC)

        async def work() -> Any:
            return await host.agent_runtime().run(
                definition(), AgentRequest(context, PROMPT)
            )

        result = run(work)
        diagnostic = _remote_chat_http_status(host, context.execution_id)
        assert diagnostic == code
        assert result.status is AgentExecutionStatus.MODEL_FAILED
        assert tls.requests == 1
    assert [row["state"] for row in remote.attempts()] == ["provider_rejected"]
    leak_free(tmp_path, result, diagnostic, remote.attempts(), log=caplog.text)


def test_agent_runtime_reaches_the_remote_plane(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        host = remote.open()

        async def work() -> Any:
            context = host.model_execution(ModelPurpose.CHAT, disclosure=SYNTHETIC)
            return await host.agent_runtime().run(
                definition(), AgentRequest(context, PROMPT)
            )

        result = run(work)
    assert result.status is AgentExecutionStatus.SUCCEEDED
    assert result.output == REPLY
    assert tls.authorized == [True]
    assert [a["state"] for a in remote.attempts()] == ["completed"]


def test_open_performs_no_network_dns_tls_or_secret_realization(
    tmp_path: Path,
) -> None:
    with (
        server() as tls,
        patch("socket.create_connection") as connect,
        patch("socket.getaddrinfo") as resolve,
        patch.object(_ProvisionedSecretSource, "_realize") as realize,
        patch.object(_CredentialFlight, "open") as handshake,
    ):
        remote = Remote(tmp_path, tls.port)
        remote.open()
        connect.assert_not_called()
        resolve.assert_not_called()
        realize.assert_not_called()
        handshake.assert_not_called()
    assert tls.connections == 0
    assert remote.attempts() == []
    assert remote.uses() == []


def test_ungoverned_adapter_of_a_remote_binding_sends_nothing(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        host = remote.open()
        adapter = host._chat.configured.adapter  # type: ignore[attr-defined]
        from legoai.intelligence.model.ports import ModelPreflightError

        with pytest.raises(ModelPreflightError):
            run(lambda: adapter.chat(ChatRequest((ChatMessage(ChatRole.USER, "x"),))))
    assert tls.connections == 0 and remote.attempts() == []


# --- Multiple invocations of one credential revision (A-D) -------------------


def test_a_same_revision_serves_chat_then_embedding_as_separate_uses(
    tmp_path: Path,
) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()

        async def work() -> tuple[Any, Any]:
            return await remote.chat(), await remote.embed()

        first, second = run(work)
    for result in (first, second):
        assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert second.execution.execution_id != first.execution.execution_id
    attempts = remote.attempts()
    assert [a["record"]["model"] for a in attempts] == ["model-a", "embed-a"]
    assert len({a["id"] for a in attempts}) == 2
    uses = remote.uses()
    assert {u.use_id.value for u in uses} == {a["id"] for a in attempts}
    assert all(u.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED for u in uses)
    assert tls.connections == 2 and tls.authorized == [True, True]


def test_a_two_chats_same_revision(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()

        async def work() -> tuple[Any, Any]:
            return await remote.chat(), await remote.chat("second")

        first, second = run(work)
    for result in (first, second):
        assert result.execution.final_state is ExecutionState.SUCCEEDED
    attempts = remote.attempts()
    assert [a["state"] for a in attempts] == ["completed", "completed"]
    assert len({a["id"] for a in attempts}) == 2
    uses = remote.uses()
    assert len(uses) == 2 and len({u.use_id for u in uses}) == 2
    assert {u.use_id.value for u in uses} == {a["id"] for a in attempts}
    assert tls.authorized == [True, True]
    # One revision served both; each use carried its own plan and attribution.
    revisions = {u.accepted_fact.plan.secret for u in uses}
    assert revisions == {remote.credential.exact}


def test_b_retired_revision_refuses_the_next_invocation_before_handoff(
    tmp_path: Path,
) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()

        async def work() -> tuple[Any, Any]:
            first = await remote.chat()
            remote.source.retire(remote.credential)
            return first, await remote.chat()

        first, second = run(work)
    assert first.execution.final_state is ExecutionState.SUCCEEDED
    not_sent(second)
    assert [a["state"] for a in remote.attempts()] == ["completed", "not_sent"]
    assert remote.attempts()[1]["observations"] == {"refused_at_gate"}
    assert len(remote.uses()) == 1  # no use was even prepared for the second
    assert tls.connections == 1
    assert remote.observation(second).effect is EffectExtent.NONE


def test_c_expired_admission_refuses_at_the_disclosure_gate(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()

        async def work() -> tuple[Any, Any]:
            first = await remote.chat()
            remote.clock.now = AT + DAY + HOUR  # admission not_after passed
            return first, await remote.chat()

        first, second = run(work)
    assert first.execution.final_state is ExecutionState.SUCCEEDED
    failed(
        second,
        EffectExtent.NONE,
        ErrorCategory.POLICY_VIOLATION,
        Recoverability.TERMINAL,
    )
    assert remote.observation(second).refusal is DisclosureRefusal.EXPIRED
    assert len(remote.attempts()) == 1 and len(remote.uses()) == 1
    assert tls.connections == 1


@pytest.mark.parametrize("kind", ["expired", "revoked", "margin"])
def test_d_secret_grant_change_refuses_the_next_invocation(
    tmp_path: Path, kind: str
) -> None:
    window = (AT - HOUR, AT + 2 * HOUR)
    with server() as tls:
        remote = Remote(tmp_path, tls.port, secret_window=window)
        remote.open()

        async def work() -> tuple[Any, Any]:
            first = await remote.chat()
            if kind == "expired":
                remote.clock.now = AT + 3 * HOUR
            elif kind == "revoked":
                # The host's own domain-ordered Grant registry (no public
                # revocation API exists); the Secret gate reads it currently.
                uses = remote.host._remote._uses
                uses._participants[2].revoke(GrantId("grant-secret"))
            else:
                # Less than the SRCP-1 margin of validity remains.
                remote.clock.now = AT + 2 * HOUR - timedelta(minutes=3)
            return first, await remote.chat()

        first, second = run(work)
    assert first.execution.final_state is ExecutionState.SUCCEEDED
    not_sent(second)
    states = [a["state"] for a in remote.attempts()]
    assert states == ["completed", "not_sent"]
    assert tls.requests == 1  # nothing credential-bearing left for the second
    assert tls.authorized == [True]
    accepted = [u for u in remote.uses() if u.accepted_fact is not None]
    assert len(accepted) == 1


# --- Open-time REMOTE admission ------------------------------------------------


def open_failure(remote: Remote, **changes: Any) -> HostFailure:
    with (
        patch("legoai.runtime.local.admit") as admit,
        pytest.raises(HostError) as error,
    ):
        remote.open(**changes)
    if error.value.failure is not HostFailure.INITIALIZATION_FAILURE:
        admit.assert_not_called()
    return error.value.failure


def test_missing_disclosure_or_admission_is_unsupported(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9)
    assert open_failure(remote, disclosure=None) is HostFailure.UNSUPPORTED_COMPOSITION
    other = replace(remote.admission, bindings=frozenset({"other"}))
    config = RemoteDisclosureConfig((remote.declaration(),), (other,))
    with pytest.raises(HostError) as error:
        remote.open(disclosure=config)
    # The admission names an unknown binding: inconsistent configuration.
    assert error.value.failure is HostFailure.INVALID_CONFIGURATION


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"provider_id": ProviderId("other-provider")}, "invalid_configuration"),
        ({"base_url": "https://other.example.org/v1"}, "invalid_configuration"),
        ({"base_url": "http://localhost:9/v1"}, "invalid_configuration"),
        ({"bearer_credential": None}, "unsupported_composition"),
    ],
    ids=["provider", "endpoint", "plaintext-http", "missing-secretref"],
)
def test_binding_mismatches_refuse_at_open(
    tmp_path: Path, changes: dict[str, Any], expected: str
) -> None:
    remote = Remote(tmp_path, 9, settings_changes=changes)
    assert open_failure(remote).value == expected


def test_wrong_secret_class_or_revision_refuses_at_open(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9)
    wrong_class = replace(remote.credential, secret_class="synthetic")
    remote.settings = replace(remote.settings, bearer_credential=wrong_class)
    assert open_failure(remote) is HostFailure.UNSUPPORTED_COMPOSITION
    forged = SecretRef(
        SecretRevisionRef(SCOPE, "remote-key", "s1-forged", "s1-map-forged"),
        remote.credential.secret_class,
        credential_purpose(),
    )
    remote.settings = replace(remote.settings, bearer_credential=forged)
    assert open_failure(remote) is HostFailure.STALE_CONFIGURATION


def test_stale_revision_after_rotation_refuses_at_open(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9)
    remote.provision()  # rotation retires the configured revision
    assert open_failure(remote) is HostFailure.STALE_CONFIGURATION


def test_wrong_secret_purpose_refuses_at_open(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9, purpose="other-purpose")
    assert open_failure(remote) is HostFailure.INVALID_CONFIGURATION


def test_missing_secret_use_grant_refuses_at_open(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9)
    remote.grants = remote.grants[:2]
    assert open_failure(remote) is HostFailure.INVALID_CONFIGURATION


def test_missing_runtime_participants_refuse_at_open(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9)
    with pytest.raises(HostError) as error:
        open_local_host(
            remote.config(),
            {"revision": "r1", "binding": "remote"},
            clock=remote.clock,
        )
    assert error.value.failure is HostFailure.UNSUPPORTED_COMPOSITION

    class Foreign:
        def provision(self, identity: str) -> SecretRef:
            raise AssertionError

        def retire(self, credential: SecretRef) -> None:
            raise AssertionError

        def close(self) -> None:
            raise AssertionError

    for runtime, failure in (
        (remote.runtime(credentials=Foreign()), HostFailure.UNSUPPORTED_COMPOSITION),
        (
            remote.runtime(custody=tmp_path / "missing"),
            HostFailure.INVALID_CONFIGURATION,
        ),
        (
            remote.runtime(trust_anchor=tmp_path / "missing.pem"),
            HostFailure.INVALID_CONFIGURATION,
        ),
    ):
        with pytest.raises(HostError) as error:
            open_local_host(
                remote.config(),
                {"revision": "r1", "binding": "remote"},
                clock=remote.clock,
                remote=runtime,
            )
        assert error.value.failure is failure


def test_margin_bounds_and_credentialed_local_refused(tmp_path: Path) -> None:
    remote = Remote(tmp_path, 9)
    for margin in (timedelta(0), timedelta(hours=2)):
        with pytest.raises(HostError):
            remote.runtime(validity_margin=margin)
    local = replace(
        remote.settings,
        base_url="http://127.0.0.1:9/v1",
        deployment=ModelDeployment.LOCAL,
    )
    remote.settings = local
    assert open_failure(remote, disclosure=None) is HostFailure.UNSUPPORTED_COMPOSITION


# --- Per-invocation failure matrix (public path) -------------------------------


def test_missing_declaration_refused_before_attempt_secret_or_network(
    tmp_path: Path,
) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        result = run(lambda: remote.chat(disclosure=None))
    failed(
        result,
        EffectExtent.NONE,
        ErrorCategory.POLICY_VIOLATION,
        Recoverability.TERMINAL,
    )
    assert remote.observation(result).refusal is DisclosureRefusal.UNCLASSIFIED
    assert remote.attempts() == [] and remote.uses() == []
    assert tls.connections == 0


@pytest.mark.parametrize(
    ("admission_changes", "purpose", "value", "refusal"),
    [
        (
            {"not_before": AT - 3 * DAY, "not_after": AT - 2 * DAY},
            "chat",
            SYNTHETIC,
            DisclosureRefusal.EXPIRED,
        ),
        (
            {"models": frozenset({"model-a"})},
            "embedding",
            SYNTHETIC,
            DisclosureRefusal.MODEL_NOT_ADMITTED,
        ),
        (
            {},
            "chat",
            ExecutionDisclosure(
                "forgeai",
                DisclosureDeclaration(
                    frozenset({DisclosureClass.REPOSITORY_CONTENT}), OTHER_REPO
                ),
            ),
            DisclosureRefusal.REPOSITORY_NOT_ADMITTED,
        ),
    ],
    ids=["expired-admission", "model-not-admitted", "repository-not-admitted"],
)
def test_disclosure_refusals_reach_nothing(
    tmp_path: Path,
    admission_changes: dict[str, Any],
    purpose: str,
    value: ExecutionDisclosure,
    refusal: DisclosureRefusal,
) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port, admission_changes=admission_changes)
        remote.open()
        call = remote.chat if purpose == "chat" else remote.embed
        result = run(lambda: call(disclosure=value))
    failed(
        result,
        EffectExtent.NONE,
        ErrorCategory.POLICY_VIOLATION,
        Recoverability.TERMINAL,
    )
    assert remote.observation(result).refusal is refusal
    assert remote.attempts() == [] and remote.uses() == []
    assert tls.connections == 0


def test_wrong_secret_consumer_refused_before_transport(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port, consumer="another-consumer")
        remote.open()
        result = run(remote.chat)
    not_sent(result)
    (attempt,) = remote.attempts()
    assert attempt["state"] == "not_sent"
    assert attempt["observations"] == {"refused_at_gate"}
    assert remote.uses() == []
    assert tls.connections == 0


def test_binding_origin_association_mismatch_fails_before_custody(
    tmp_path: Path,
) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        host = remote.open()
        plane = host._remote  # type: ignore[attr-defined]
        plane._association = replace(
            plane._association, endpoint_origin="https://other.example.org"
        )
        with patch.object(_ProvisionedSecretSource, "_realize") as realize:
            result = run(remote.chat)
        realize.assert_not_called()
    not_sent(result)
    assert remote.attempts() == [] and remote.uses() == []
    assert tls.connections == 0
    assert remote.observation(result).effect is EffectExtent.NONE


def test_intended_commit_failure_sends_nothing(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        with (
            patch.object(
                _RemoteAttemptStore,
                "intend",
                side_effect=_StorageGap("attempt commit requires inspection"),
            ),
            patch.object(_ProvisionedSecretSource, "_realize") as realize,
        ):
            result = run(remote.chat)
        realize.assert_not_called()
    not_sent(result)
    assert remote.attempts() == [] and remote.uses() == []
    assert tls.connections == 0


def test_one_exchange_per_invocation(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        host = remote.open()
        plane = host._remote  # type: ignore[attr-defined]
        calls: list[tuple[int, bytes]] = []

        async def work() -> None:
            context = host.model_execution(ModelPurpose.CHAT, disclosure=SYNTHETIC)
            check = host._check(context, ModelPurpose.CHAT, SYNTHETIC)  # type: ignore[attr-defined]
            invocation = _Invocation(
                plane, check, check.decide(), ModelPurpose.CHAT.capability_id
            )
            calls.append(invocation.exchange(CHAT_PATH[3:], b'{"model":"model-a"}'))
            from legoai.intelligence.model.ports import ModelPreflightError

            with pytest.raises(ModelPreflightError):
                invocation.exchange(CHAT_PATH[3:], b"{}")

        run(work)
    assert len(calls) == 1 and tls.requests == 1
    assert len(remote.attempts()) == 1


@pytest.mark.parametrize("cert", ["untrusted.pem", "wrong-host.pem"])
def test_tls_failures_are_not_sent_without_realization(
    tmp_path: Path, cert: str
) -> None:
    with server(cert=cert) as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        with patch.object(_ProvisionedSecretSource, "_realize") as realize:
            result = run(remote.chat)
        realize.assert_not_called()
    not_sent(result)
    (attempt,) = remote.attempts()
    assert attempt["state"] == "not_sent" and attempt["observations"] == {"sent_none"}
    assert all(u.accepted_fact is None for u in remote.uses())
    assert tls.requests == 0
    assert remote.observation(result).effect is EffectExtent.NONE


def test_connection_failure_is_not_sent(tmp_path: Path) -> None:
    family, _, _, _, address = socket.getaddrinfo(
        "localhost", 0, type=socket.SOCK_STREAM
    )[0]
    probe = socket.create_server((address[0], 0), family=family)
    port = probe.getsockname()[1]
    probe.close()
    remote = Remote(tmp_path, port, timeout=3.0)
    remote.open()
    result = run(remote.chat)
    not_sent(result)
    assert [a["state"] for a in remote.attempts()] == ["not_sent"]


@contextmanager
def silent_listener() -> Iterator[int]:
    """Accepts TCP and never speaks TLS: the handshake can only time out."""
    family, _, _, _, address = socket.getaddrinfo(
        "localhost", 0, type=socket.SOCK_STREAM
    )[0]
    listener = socket.create_server((address[0], 0), family=family)
    accepted: list[socket.socket] = []
    stop = threading.Event()

    def accept() -> None:
        listener.settimeout(0.2)
        while not stop.is_set():
            try:
                conn, _ = listener.accept()
                accepted.append(conn)
            except TimeoutError, OSError:
                continue

    thread = threading.Thread(target=accept, daemon=True)
    thread.start()
    try:
        yield listener.getsockname()[1]
    finally:
        stop.set()
        listener.close()
        thread.join(5)
        for conn in accepted:
            conn.close()


def test_timeout_before_send_is_not_sent(tmp_path: Path) -> None:
    with silent_listener() as port:
        remote = Remote(tmp_path, port, timeout=1.0)
        remote.open()
        result = run(remote.chat)
    not_sent(result)
    (attempt,) = remote.attempts()
    assert attempt["state"] == "not_sent" and attempt["observations"] == {"sent_none"}


def test_partial_send_interrupted_by_retirement_stays_unknown(tmp_path: Path) -> None:
    original_send = _CredentialFlight._send_some
    original_wait = _CredentialFlight._wait_writable
    waits = {"n": 0}
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()

        def send(flight: _CredentialFlight, data: bytes) -> int:
            return original_send(flight, data[:1000])

        def wait(flight: _CredentialFlight) -> None:
            waits["n"] += 1
            if waits["n"] == 2:
                remote.source.retire(remote.credential)  # public, domain-ordered
            original_wait(flight)

        with (
            patch.object(_CredentialFlight, "_send_some", send),
            patch.object(_CredentialFlight, "_wait_writable", wait),
        ):
            result = run(lambda: remote.chat("x" * 20_000))
    failed(
        result,
        EffectExtent.UNKNOWN,
        ErrorCategory.DEPENDENCY_FAILURE,
        Recoverability.REQUIRES_INTERVENTION,
    )
    (attempt,) = remote.attempts()
    assert attempt["state"] == "unknown" and "sent_partial" in attempt["observations"]
    (use,) = remote.uses()
    assert use.accepted_fact is not None  # bytes left: the use is never denied
    assert tls.connections == 1
    assert remote.observation(result).effect is EffectExtent.UNKNOWN


@pytest.mark.parametrize(
    ("mode", "recoverability"),
    [
        ("401", Recoverability.TERMINAL),
        ("403", Recoverability.TERMINAL),
        ("404", Recoverability.TERMINAL),
        ("405", Recoverability.TERMINAL),
        ("418", Recoverability.TERMINAL),
        ("500", Recoverability.TERMINAL),
        ("429", Recoverability.POTENTIALLY_RETRYABLE),
        ("503", Recoverability.POTENTIALLY_RETRYABLE),
    ],
)
def test_complete_provider_rejections_are_never_retried(
    tmp_path: Path, mode: str, recoverability: Recoverability
) -> None:
    # The error body echoes the canary: it must never be decoded or retained.
    echo = json.dumps({"error": {"message": f"bad key {CANARY}"}}).encode()
    with server(mode, responses={CHAT_PATH: echo}) as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        result = run(remote.chat)
    failed(result, EffectExtent.NONE, ErrorCategory.DEPENDENCY_FAILURE, recoverability)
    (attempt,) = remote.attempts()
    assert attempt["state"] == "provider_rejected"
    assert _remote_chat_http_status(remote.host, result.execution.execution_id) == int(
        mode
    )
    assert attempt["observations"] == {"sent_all", "response_complete"}
    (use,) = remote.uses()
    assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
    assert tls.connections == 1 and tls.requests == 1  # no retry, no fallback
    assert remote.observation(result).effect is EffectExtent.COMPLETED
    leak_free(tmp_path, result, result.execution)


@pytest.mark.parametrize(
    "body",
    [
        b"not json",
        chat_body(model="other-model"),
        chat_body(finish="length"),
        b'{"model":"model-a","choices":[]}',
    ],
    ids=["malformed-json", "wrong-model", "finish-reason", "no-choice"],
)
def test_complete_2xx_rejected_by_the_shared_parser(
    tmp_path: Path, body: bytes
) -> None:
    with server(responses={CHAT_PATH: body}) as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        result = run(remote.chat)
    failed(
        result,
        EffectExtent.NONE,
        ErrorCategory.DEPENDENCY_FAILURE,
        Recoverability.TERMINAL,
    )
    # Transport truth is not rewritten by a later protocol rejection.
    (attempt,) = remote.attempts()
    assert attempt["state"] == "completed"
    assert tls.requests == 1
    assert _remote_chat_http_status(remote.host, result.execution.execution_id) == 200


def test_embedding_shape_failure_rejected(tmp_path: Path) -> None:
    with server(responses={EMBED_PATH: embed_body(count=1)}) as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()
        result = run(lambda: remote.embed(("alpha", "beta")))
    failed(
        result,
        EffectExtent.NONE,
        ErrorCategory.DEPENDENCY_FAILURE,
        Recoverability.TERMINAL,
    )
    assert [a["state"] for a in remote.attempts()] == ["completed"]


@pytest.mark.parametrize(
    "mode", ["truncated", "malformed", "malformed-chunk", "timeout", "199", "600"]
)
def test_sent_without_a_complete_response_is_unknown(tmp_path: Path, mode: str) -> None:
    with server(mode) as tls:
        remote = Remote(tmp_path, tls.port, timeout=1.0)
        remote.open()
        result = run(remote.chat)
    failed(
        result,
        EffectExtent.UNKNOWN,
        ErrorCategory.DEPENDENCY_FAILURE,
        Recoverability.REQUIRES_INTERVENTION,
    )
    (attempt,) = remote.attempts()
    assert attempt["state"] == "unknown"
    assert attempt["observations"] == {"sent_all", "response_incomplete"}
    (use,) = remote.uses()
    assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
    assert tls.connections == 1  # no retry
    assert remote.observation(result).effect is EffectExtent.UNKNOWN
    assert _remote_chat_http_status(remote.host, result.execution.execution_id) is None


def test_cancellation_before_send_reaches_nothing(tmp_path: Path) -> None:
    with server() as tls:
        remote = Remote(tmp_path, tls.port)
        remote.open()

        async def work() -> None:
            task = asyncio.create_task(remote.chat())
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        run(work)
    assert remote.attempts() == [] and remote.uses() == []
    assert tls.connections == 0


@pytest.mark.parametrize(
    ("mode", "state"), [("ok", "completed"), ("timeout", "unknown")]
)
def test_cancellation_after_send_never_rewrites_recorded_truth(
    tmp_path: Path, mode: str, state: str
) -> None:
    holder: dict[str, Any] = {}

    def cancel() -> None:
        holder["loop"].call_soon_threadsafe(holder["task"].cancel)

    with server(mode, on_request=cancel) as tls:
        remote = Remote(tmp_path, tls.port, timeout=1.0)
        remote.open()

        async def work() -> None:
            holder["loop"] = asyncio.get_running_loop()
            holder["task"] = asyncio.create_task(remote.chat())
            try:
                await holder["task"]
            except asyncio.CancelledError:
                pass

        run(work)
    (attempt,) = remote.attempts()
    assert attempt["state"] == state
    (use,) = remote.uses()
    assert use.category is UseRecoveryCategory.ACCEPTED_ATTRIBUTED
    assert tls.connections == 1 and tls.requests == 1


# --- Containment and ambient inputs ------------------------------------------


def test_ambient_inputs_are_ignored_on_the_public_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for name in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY"):
        monkeypatch.setenv(name, "http://127.0.0.1:9")
    monkeypatch.setenv("NO_PROXY", "")
    monkeypatch.setenv("SSLKEYLOGFILE", str(tmp_path / "keys.log"))
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("CURL_CA_BUNDLE", str(tmp_path / "missing.pem"))
    monkeypatch.setenv("OPENAI_API_KEY", "ambient-must-never-be-used")
    monkeypatch.setenv("KISSKI_API_KEY", "ambient-must-never-be-used")
    custody = tmp_path / "custody"
    custody.mkdir()
    with server() as tls:
        remote = Remote(custody, tls.port)
        remote.open()
        result = run(remote.chat)
    assert result.execution.final_state is ExecutionState.SUCCEEDED
    assert tls.authorized == [True]  # the provisioned credential only
    assert not (tmp_path / "keys.log").exists()


def test_local_bindings_need_no_remote_participants_and_create_nothing(
    tmp_path: Path,
) -> None:
    remote = Remote(tmp_path / "unused", 9)
    (tmp_path / "unused").mkdir()
    local = ModelBindingConfig(
        "local",
        PROFILE,
        OpenAICompatibleSettings(
            "http://127.0.0.1:9/v1",
            "model-a",
            None,
            5.0,
            None,
            ProviderId("local"),
            ModelDeployment.LOCAL,
        ),
    )
    config = replace(remote.config(), bindings=(local,), disclosure=None)
    host = open_local_host(
        config, {"revision": "r1", "binding": "local"}, remote=remote.runtime()
    )
    assert host._gate is None and host._remote is None  # type: ignore[attr-defined]
    assert list((tmp_path / "unused").iterdir()) == []
