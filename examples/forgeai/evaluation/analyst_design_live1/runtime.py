"""One governed Agent call; supervised process bounds blocking client I/O."""

import asyncio
import hashlib
import json
import multiprocessing
import os
import time
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from multiprocessing.connection import Connection
from typing import Any
from urllib.request import (
    HTTPRedirectHandler,
    ProxyHandler,
    build_opener,
    install_opener,
)

from analyst_design_eval2.data import Fixture, input_facts
from analyst_design_eval2.inputs import expected_payload
from content_discovery1.wiring import Replay, host_for
from forgeai.cli import ollama_binding
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceSufficiencyResult,
)
from legoai_engineering.analyst.sufficiency_agent import EvidenceSufficiencyAgent
from legoai_engineering.analyst.sufficiency_definition import (
    evidence_sufficiency_definition,
)

from analyst_design_live1.identity import MODEL, URL
from legoai.execution.agent.ports import (
    AgentDefinition,
    AgentRequest,
    AgentResult,
    AgentRuntimePort,
)
from legoai.governance.values import GrantId, PolicyRef
from legoai.kernel.identity import ApplicationId, PrincipalId, TenantId
from legoai.kernel.references import (
    ApplicationRef,
    ConfigurationRef,
    ConfigurationRevisionRef,
    PrincipalRef,
    ReferenceScope,
)
from legoai.kernel.versions import Version
from legoai.runtime.api import LocalHostConfig, ModelPurpose, OperatorGrant
from legoai.runtime.local import open_local_host


def projection(
    m: EvidenceManifest, f: Fixture, variant: str, phase: str
) -> dict[str, Any]:
    facts = input_facts(f.id)
    paths = set(facts.selected_paths)
    if variant == "unrelated":
        paths.add(f.unrelated)
    if phase == "final" and f.addition:
        paths.add(f.addition)
    if {x.path for x in m.evidence.files} != paths:
        raise ValueError("LEAKAGE_PATHS")
    if any(x.text != f.files[x.path] for x in m.evidence.files):
        raise ValueError("LEAKAGE_CONTENT")
    expected_question = (
        f.revised_question if phase == "final" and f.clarification else facts.question
    )
    if m.question != expected_question or m.unknowns != facts.unknowns:
        raise ValueError("LEAKAGE_QUESTION")
    # Start with the independently frozen input-facts projection. Later changes
    # are limited to the manifest produced by the qualified authorized sequence.
    obj = expected_payload(replace(facts, selected_paths=tuple(paths)), m.evidence)
    obj["question"] = expected_question
    if phase == "initial" and (
        m.clarifications or m.expectations != facts.expectations
    ):
        raise ValueError("LEAKAGE_DECLARATION")
    if phase == "final":
        if not f.clarification and m.clarifications:
            raise ValueError("LEAKAGE_CLARIFICATION")
        if len(m.clarifications) != int(bool(f.clarification)):
            raise ValueError("LEAKAGE_CLARIFICATION")
        obj["clarifications"] = [
            {
                "key": x.key,
                "request": {
                    "kind": x.request.kind.value,
                    "description": x.request.description,
                    "path": None,
                    "choices": list(x.request.choices),
                },
                "answer": x.answer,
            }
            for x in m.clarifications
        ]
        if m.expectations != facts.expectations:
            raise ValueError("LEAKAGE_EXPECTATION")
    return obj


class GuardedRuntime:
    def __init__(self, runtime: AgentRuntimePort, expected: dict[str, Any]) -> None:
        self.runtime, self.expected = runtime, expected
        self.payload_digest: str | None = None
        self.calls = 0

    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult:
        if (
            definition != evidence_sufficiency_definition()
            or json.loads(request.text) != self.expected
        ):
            raise ValueError("LEAKAGE_OR_AGENT_IDENTITY")
        if self.calls:
            raise ValueError("SECOND_CALL_FORBIDDEN")
        self.calls += 1
        self.payload_digest = hashlib.sha256(request.text.encode()).hexdigest()
        return await self.runtime.run(definition, request)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(
        self, req: Any, fp: Any, code: int, msg: str, headers: Any, newurl: str
    ) -> None:
        raise ValueError("REDIRECT_FORBIDDEN")


async def governed(
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    output: str | None = None,
) -> tuple[EvidenceSufficiencyResult, str | None]:
    if output is not None:
        host, _ = host_for(Replay(output))
    else:
        if os.environ.get("FORGEAI_LIVE1_OFFLINE") == "1":
            raise ValueError("OFFLINE_PROVIDER_FORBIDDEN")
        # Process-local transport confinement; never mutate the parent's opener.
        install_opener(build_opener(ProxyHandler({}), NoRedirect()))
        now = datetime.now(UTC)
        ref = ConfigurationRef(
            ApplicationRef(
                ReferenceScope("operator", TenantId("sufficiency-live")),
                ApplicationId("sufficiency-live"),
            ),
            "assessment",
        )
        host = open_local_host(
            LocalHostConfig(
                ConfigurationRevisionRef(ref, "live1", Version(1, 0, 0)),
                PrincipalRef("operator", PrincipalId("evaluation")),
                PolicyRef("operator", "sufficiency-live", Version(1, 0, 0)),
                (
                    OperatorGrant(
                        GrantId("chat"),
                        "invoke-capability",
                        ModelPurpose.CHAT.capability_id.value,
                        now - timedelta(seconds=1),
                        now + timedelta(seconds=timeout + 10),
                    ),
                ),
                (ollama_binding(URL, MODEL, timeout),),
                max_executions=1,
            ),
            {"revision": "live1"},
            clock=lambda: datetime.now(UTC),
        )
    guard = GuardedRuntime(host.agent_runtime(), expected)
    result = await EvidenceSufficiencyAgent(guard).assess(
        host.model_execution(ModelPurpose.CHAT), m, current_manifest=lambda: m
    )
    return result, guard.payload_digest


def child(
    pipe: Connection,
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    output: str | None,
) -> None:
    try:
        result, payload_digest = asyncio.run(governed(m, expected, timeout, output))
        pipe.send((result, payload_digest, None))
    except BaseException as error:
        # Safe category only: no arbitrary exception text or raw model content.
        pipe.send((None, None, type(error).__name__))
    finally:
        pipe.close()


class CallStopped(RuntimeError):
    def __init__(self, reason: str, disposition: str) -> None:
        self.reason, self.disposition = reason, disposition
        super().__init__(reason)


def supervised(
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    *,
    output: str | None = None,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[EvidenceSufficiencyResult, str | None]:
    if timeout <= 0:
        raise CallStopped("deadline", "NOT_STARTED")
    ctx = multiprocessing.get_context("spawn")
    reader, writer = ctx.Pipe(duplex=False)
    process = ctx.Process(target=child, args=(writer, m, expected, timeout, output))
    start = clock()
    process.start()
    writer.close()
    try:
        while not reader.poll(min(0.05, max(0.0, timeout - (clock() - start)))):
            if not process.is_alive():
                raise CallStopped("child_exit", "SERVER_EFFECT_UNKNOWN")
            if clock() - start >= timeout:
                raise CallStopped("timeout", "SERVER_EFFECT_UNKNOWN")
        result, payload_digest, error = reader.recv()
        if error or not isinstance(result, EvidenceSufficiencyResult):
            raise CallStopped("child_failure", "SERVER_EFFECT_UNKNOWN")
        return result, payload_digest
    except KeyboardInterrupt:
        raise CallStopped("interrupted", "SERVER_EFFECT_UNKNOWN") from None
    finally:
        reader.close()
        if process.is_alive():
            process.terminate()
        process.join(0.5)
        if process.is_alive():
            process.kill()
            process.join(0.5)
        if process.is_alive():
            raise CallStopped(
                "client_termination_unconfirmed", "CLIENT_AND_SERVER_UNKNOWN"
            )
        process.close()
