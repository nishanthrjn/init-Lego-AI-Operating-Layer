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

from analyst_design_live1.diagnostics import (
    SAFE_CLASSES,
    ChildDiagnostics,
    ChildStage,
    Cleanup,
    FailureCategory,
    IPCStatus,
    classify,
    safe_class,
)
from analyst_design_live1.identity import MODEL, URL
from analyst_design_live1.output_diagnostics import DIAGNOSED, OutputDiagnosis, diagnose
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
    def __init__(
        self,
        runtime: AgentRuntimePort,
        expected: dict[str, Any],
        mark: Callable[[ChildStage], None],
    ) -> None:
        self.runtime, self.expected = runtime, expected
        self.mark = mark
        self.payload_digest: str | None = None
        self.calls = 0
        # Transient, in-memory only: read once for PARSER-DIAGNOSTICS-1, then
        # discarded. Never persisted or sent to the parent.
        self.result: AgentResult | None = None

    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult:
        self.mark(ChildStage.PAYLOAD_GUARD_STARTED)
        if (
            definition != evidence_sufficiency_definition()
            or json.loads(request.text) != self.expected
        ):
            raise ValueError("LEAKAGE_OR_AGENT_IDENTITY")
        if self.calls:
            raise ValueError("SECOND_CALL_FORBIDDEN")
        self.calls += 1
        self.payload_digest = hashlib.sha256(request.text.encode()).hexdigest()
        self.mark(ChildStage.PAYLOAD_GUARD_COMPLETED)
        self.mark(ChildStage.GOVERNED_RUNTIME_ENTERED)
        self.result = await self.runtime.run(definition, request)
        return self.result


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
    *,
    mark: Callable[[ChildStage], None] = lambda stage: None,
) -> tuple[EvidenceSufficiencyResult, str | None, OutputDiagnosis | None]:
    mark(ChildStage.HOST_COMPOSITION_STARTED)
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
            {"revision": "live1", "binding": "ollama"},
            clock=lambda: datetime.now(UTC),
        )
    mark(ChildStage.HOST_COMPOSITION_COMPLETED)
    guard = GuardedRuntime(host.agent_runtime(), expected, mark)
    mark(ChildStage.AGENT_CALL_STARTED)
    result = await EvidenceSufficiencyAgent(guard).assess(
        host.model_execution(ModelPurpose.CHAT), m, current_manifest=lambda: m
    )
    # Observation only: the Agent's result is final before this label exists.
    diagnosis = diagnose(result.failure, guard.result, m)
    guard.result = None
    mark(ChildStage.RESULT_COMPLETED)
    return result, guard.payload_digest, diagnosis


def child(
    pipe: Connection,
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    output: str | None,
) -> None:
    stage: ChildStage | None = None

    def mark(value: ChildStage) -> None:
        nonlocal stage
        stage = value
        pipe.send(("stage", value))

    try:
        mark(ChildStage.CHILD_STARTED)
        result, digest, diagnosis = asyncio.run(
            governed(m, expected, timeout, output, mark=mark)
        )
        pipe.send(("result", result, digest, diagnosis))
    except BaseException as error:
        pipe.send(("failure", classify(stage), safe_class(error)))
    finally:
        pipe.close()


class CallStopped(RuntimeError):
    def __init__(
        self, reason: str, disposition: str, diagnostics: ChildDiagnostics | None = None
    ) -> None:
        self.reason, self.disposition = reason, disposition
        self.diagnostics = diagnostics or ChildDiagnostics()
        super().__init__(reason)


def supervised(
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    *,
    output: str | None = None,
    clock: Callable[[], float] = time.monotonic,
    observe: Callable[[dict[str, Any]], None] = lambda record: None,
) -> tuple[EvidenceSufficiencyResult, str | None]:
    diagnostics = ChildDiagnostics()
    if timeout <= 0:
        raise CallStopped("deadline", "NOT_STARTED", diagnostics)
    ctx = multiprocessing.get_context("spawn")
    reader, writer = ctx.Pipe(duplex=False)
    process = ctx.Process(target=child, args=(writer, m, expected, timeout, output))
    start = clock()
    started = False

    def stop(reason: str, category: FailureCategory) -> CallStopped:
        diagnostics.failure = category
        return CallStopped(reason, "SERVER_EFFECT_UNKNOWN", diagnostics)

    try:
        try:
            process.start()
            started = True
        except Exception as error:
            diagnostics.exception_class = safe_class(error)
            raise stop(
                "child_failure", FailureCategory.PROCESS_LAUNCH_FAILURE
            ) from None
        finally:
            writer.close()
        while True:
            if clock() - start >= timeout:
                raise stop("timeout", FailureCategory.TIMEOUT)
            try:
                ready = reader.poll(min(0.05, max(0.0, timeout - (clock() - start))))
                if not ready:
                    if not process.is_alive():
                        category = (
                            FailureCategory.CHILD_PROTOCOL_FAILURE
                            if process.exitcode == 0
                            else FailureCategory.CHILD_ABNORMAL_EXIT
                            if process.exitcode is not None
                            else FailureCategory.UNKNOWN_CHILD_FAILURE
                        )
                        raise stop("child_exit", category)
                    continue
                envelope = reader.recv()
            except EOFError:
                diagnostics.ipc = IPCStatus.EOF_BEFORE_ENVELOPE
                raise stop(
                    "child_failure", FailureCategory.CHILD_PROTOCOL_FAILURE
                ) from None
            except OSError:
                diagnostics.ipc = IPCStatus.PIPE_ERROR
                raise stop(
                    "child_failure", FailureCategory.CHILD_PROTOCOL_FAILURE
                ) from None
            if not isinstance(envelope, tuple) or not envelope:
                diagnostics.ipc = IPCStatus.INVALID_ENVELOPE
                raise stop("child_failure", FailureCategory.CHILD_PROTOCOL_FAILURE)
            kind = envelope[0]
            if (
                kind == "stage"
                and len(envelope) == 2
                and isinstance(envelope[1], ChildStage)
            ):
                stages = list(ChildStage)
                previous = stages.index(diagnostics.stage) if diagnostics.stage else -1
                if stages.index(envelope[1]) != previous + 1 and not (
                    envelope[1] == ChildStage.RESULT_COMPLETED
                    and diagnostics.stage == ChildStage.AGENT_CALL_STARTED
                ):
                    diagnostics.ipc = IPCStatus.INVALID_ENVELOPE
                    raise stop("child_failure", FailureCategory.CHILD_PROTOCOL_FAILURE)
                diagnostics.stage = envelope[1]
                observe(diagnostics.record())
                continue
            if (
                kind == "failure"
                and len(envelope) == 3
                and isinstance(envelope[1], FailureCategory)
                and isinstance(envelope[2], str)
                and envelope[2] in SAFE_CLASSES | {"OtherException"}
            ):
                diagnostics.ipc = IPCStatus.ENVELOPE_RECEIVED
                diagnostics.exception_class = envelope[2]
                raise stop("child_failure", envelope[1])
            if kind == "result" and len(envelope) == 4:
                diagnostics.ipc = IPCStatus.ENVELOPE_RECEIVED
                result, digest, diagnosis = envelope[1:]
                if (
                    not isinstance(result, EvidenceSufficiencyResult)
                    or (
                        diagnosis is not None and type(diagnosis) is not OutputDiagnosis
                    )
                    or (diagnosis is not None) != (result.failure in DIAGNOSED)
                    or diagnostics.stage != ChildStage.RESULT_COMPLETED
                    or (
                        digest is not None
                        and (
                            not isinstance(digest, str)
                            or len(digest) != 64
                            or any(c not in "0123456789abcdef" for c in digest)
                        )
                    )
                ):
                    raise stop("child_failure", FailureCategory.INVALID_RESULT)
                diagnostics.output = diagnosis
                return result, digest
            diagnostics.ipc = IPCStatus.INVALID_ENVELOPE
            raise stop("child_failure", FailureCategory.CHILD_PROTOCOL_FAILURE)
    except KeyboardInterrupt:
        raise stop("interrupted", FailureCategory.UNKNOWN_CHILD_FAILURE) from None
    finally:
        reader.close()
        if started:
            # Give an envelope-sending child a bounded chance to exit normally.
            # Cleanup is separate from the envelope and from provider effect truth.
            if diagnostics.ipc != IPCStatus.NO_ENVELOPE:
                process.join(0.5)
            if process.is_alive():
                diagnostics.cleanup = Cleanup.TERMINATE
                process.terminate()
            process.join(0.5)
            if process.is_alive():
                diagnostics.cleanup = Cleanup.KILL
                process.kill()
                process.join(0.5)
            diagnostics.exitcode = process.exitcode
            if (
                diagnostics.ipc == IPCStatus.EOF_BEFORE_ENVELOPE
                and diagnostics.exitcode not in {None, 0}
                and diagnostics.cleanup == Cleanup.NONE
            ):
                diagnostics.failure = FailureCategory.CHILD_ABNORMAL_EXIT
            if process.is_alive():
                observe(diagnostics.record())
                raise CallStopped(
                    "client_termination_unconfirmed",
                    "CLIENT_AND_SERVER_UNKNOWN",
                    diagnostics,
                )
        process.close()
        observe(diagnostics.record())
