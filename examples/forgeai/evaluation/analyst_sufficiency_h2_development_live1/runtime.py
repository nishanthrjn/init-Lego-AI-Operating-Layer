"""One governed Agent 1.1.0 call; supervised process bounds blocking client I/O.

The qualified LIVE-1 runtime (analyst_design_live1.runtime) pins Agent 1.0.0
in its payload guard and child, so it cannot run 1.1.0 unchanged and is not
edited. This module is its 1.1.0 counterpart with the same stages, failure
categories, diagnostics, supervision and cleanup, reusing those types
unchanged. Two additions: the guard pins the 1.1.0 definition and envelope,
and an H3-absence check refuses, before sending, any provider request that
carries a structured-output requirement.
"""

import asyncio
import hashlib
import json
import multiprocessing
import os
import time
import urllib.request
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from multiprocessing.connection import Connection
from typing import Any

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
from analyst_design_live1.output_diagnostics import DIAGNOSED, OutputDiagnosis, diagnose
from analyst_design_live1.runtime import CallStopped, NoRedirect
from content_discovery1.wiring import Replay, host_for
from forgeai.cli import ollama_binding
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceSufficiencyResult,
)
from legoai_engineering.analyst.sufficiency_envelope import (
    EnvelopedEvidenceSufficiencyAgent,
    enveloped_sufficiency_definition,
)

from analyst_sufficiency_h2_development_live1.identity import MODEL, URL
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

__all__ = ["H3_ABSENT", "CallStopped", "governed", "supervised"]
H3_ABSENT = "NO_STRUCTURED_OUTPUT_REQUIREMENT"


class GuardedRuntime:
    """Pins the exact 1.1.0 definition and payload; at most one call."""

    def __init__(
        self,
        runtime: AgentRuntimePort,
        expected: dict[str, Any],
        mark: Callable[[ChildStage], None],
    ) -> None:
        self.runtime, self.expected, self.mark = runtime, expected, mark
        self.payload_digest: str | None = None
        self.calls = 0
        # Transient and in memory only: read once for output diagnostics.
        self.result: AgentResult | None = None

    async def run(
        self, definition: AgentDefinition, request: AgentRequest
    ) -> AgentResult:
        self.mark(ChildStage.PAYLOAD_GUARD_STARTED)
        if (
            definition != enveloped_sufficiency_definition()
            or definition.behavior_version != Version(1, 1, 0)
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


class WireCheck:
    """Process-local pass-through: refuses a `format` field before sending."""

    def __init__(self) -> None:
        self.original = urllib.request.urlopen
        self.requests = 0
        self.violation = False

    def __call__(self, request: Any, *args: Any, **kwargs: Any) -> Any:
        if "format" in json.loads(request.data):
            self.violation = True  # re-raised by `governed` even if wrapped
            raise ValueError("H3_STRUCTURED_OUTPUT_PRESENT")
        self.requests += 1
        return self.original(request, *args, **kwargs)


def _live_host(timeout: float) -> Any:
    now = datetime.now(UTC)
    ref = ConfigurationRef(
        ApplicationRef(
            ReferenceScope("operator", TenantId("h2-development")),
            ApplicationId("h2-development"),
        ),
        "assessment",
    )
    return open_local_host(
        LocalHostConfig(
            ConfigurationRevisionRef(ref, "h2dev1", Version(1, 0, 0)),
            PrincipalRef("operator", PrincipalId("evaluation")),
            PolicyRef("operator", "h2-development", Version(1, 0, 0)),
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
        {"revision": "h2dev1", "binding": "ollama"},
        clock=lambda: datetime.now(UTC),
    )


async def governed(
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    output: str | None = None,
    *,
    mark: Callable[[ChildStage], None] = lambda stage: None,
) -> tuple[EvidenceSufficiencyResult, str | None, OutputDiagnosis | None, str]:
    mark(ChildStage.HOST_COMPOSITION_STARTED)
    replay: Replay | None = None
    wire: WireCheck | None = None
    if output is not None:
        replay = Replay(output)
        host, _ = host_for(replay)
    else:
        if os.environ.get("FORGEAI_LIVE1_OFFLINE") == "1":
            raise ValueError("OFFLINE_PROVIDER_FORBIDDEN")
        # Process-local confinement; never mutates the parent's opener.
        urllib.request.install_opener(
            urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
        )
        wire = WireCheck()
        urllib.request.urlopen = wire  # type: ignore[assignment]
        host = _live_host(timeout)
    mark(ChildStage.HOST_COMPOSITION_COMPLETED)
    guard = GuardedRuntime(host.agent_runtime(), expected, mark)
    mark(ChildStage.AGENT_CALL_STARTED)
    result = await EnvelopedEvidenceSufficiencyAgent(guard).assess(
        host.model_execution(ModelPurpose.CHAT), m, current_manifest=lambda: m
    )
    if replay is not None and any(
        r.response_format is not None for r in replay.requests
    ):
        raise ValueError("H3_STRUCTURED_OUTPUT_PRESENT")
    if wire is not None and wire.violation:
        raise ValueError("H3_STRUCTURED_OUTPUT_PRESENT")
    if wire is not None and wire.requests > 1:
        raise ValueError("SECOND_CALL_FORBIDDEN")
    diagnosis = diagnose(result.failure, guard.result, m)
    guard.result = None
    mark(ChildStage.RESULT_COMPLETED)
    return result, guard.payload_digest, diagnosis, H3_ABSENT


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
        result, digest, diagnosis, h3 = asyncio.run(
            governed(m, expected, timeout, output, mark=mark)
        )
        pipe.send(("result", result, digest, diagnosis, h3))
    except BaseException as error:
        pipe.send(("failure", classify(stage), safe_class(error)))
    finally:
        pipe.close()


def supervised(
    m: EvidenceManifest,
    expected: dict[str, Any],
    timeout: float,
    *,
    output: str | None = None,
    clock: Callable[[], float] = time.monotonic,
    observe: Callable[[dict[str, Any]], None] = lambda record: None,
) -> tuple[EvidenceSufficiencyResult, str | None, str]:
    """LIVE-1 supervision semantics, unchanged, around the 1.1.0 child."""
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
            if kind == "result" and len(envelope) == 5:
                diagnostics.ipc = IPCStatus.ENVELOPE_RECEIVED
                result, digest, diagnosis, h3 = envelope[1:]
                if (
                    not isinstance(result, EvidenceSufficiencyResult)
                    or h3 != H3_ABSENT
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
                return result, digest, h3
            diagnostics.ipc = IPCStatus.INVALID_ENVELOPE
            raise stop("child_failure", FailureCategory.CHILD_PROTOCOL_FAILURE)
    except KeyboardInterrupt:
        raise stop("interrupted", FailureCategory.UNKNOWN_CHILD_FAILURE) from None
    finally:
        reader.close()
        if started:
            # A bounded chance for an envelope-sending child to exit normally.
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
