"""Closed, content-free child diagnostic custody; no provider receipt claims."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from analyst_design_live1.output_diagnostics import OutputDiagnosis


class ChildStage(StrEnum):
    CHILD_STARTED = "CHILD_STARTED"
    HOST_COMPOSITION_STARTED = "HOST_COMPOSITION_STARTED"
    HOST_COMPOSITION_COMPLETED = "HOST_COMPOSITION_COMPLETED"
    AGENT_CALL_STARTED = "AGENT_CALL_STARTED"
    PAYLOAD_GUARD_STARTED = "PAYLOAD_GUARD_STARTED"
    PAYLOAD_GUARD_COMPLETED = "PAYLOAD_GUARD_COMPLETED"
    GOVERNED_RUNTIME_ENTERED = "GOVERNED_RUNTIME_ENTERED"
    RESULT_COMPLETED = "RESULT_COMPLETED"


class FailureCategory(StrEnum):
    PROCESS_LAUNCH_FAILURE = "PROCESS_LAUNCH_FAILURE"
    BOOTSTRAP_FAILURE = "BOOTSTRAP_FAILURE"
    COMPOSITION_FAILURE = "COMPOSITION_FAILURE"
    PRE_DISPATCH_AGENT_FAILURE = "PRE_DISPATCH_AGENT_FAILURE"
    TRANSPORT_FAILURE = "TRANSPORT_FAILURE"
    TIMEOUT = "TIMEOUT"
    CHILD_ABNORMAL_EXIT = "CHILD_ABNORMAL_EXIT"
    CHILD_PROTOCOL_FAILURE = "CHILD_PROTOCOL_FAILURE"
    INVALID_RESULT = "INVALID_RESULT"
    UNKNOWN_CHILD_FAILURE = "UNKNOWN_CHILD_FAILURE"


class IPCStatus(StrEnum):
    NO_ENVELOPE = "NO_ENVELOPE"
    ENVELOPE_RECEIVED = "ENVELOPE_RECEIVED"
    EOF_BEFORE_ENVELOPE = "EOF_BEFORE_ENVELOPE"
    INVALID_ENVELOPE = "INVALID_ENVELOPE"
    PIPE_ERROR = "PIPE_ERROR"


class Cleanup(StrEnum):
    NONE = "NONE"
    TERMINATE = "TERMINATE"
    KILL = "KILL"


SAFE_CLASSES = frozenset(
    {
        "HostError",
        "ModelCompositionError",
        "ValueError",
        "TypeError",
        "OSError",
        "TimeoutError",
        "KeyboardInterrupt",
    }
)


def safe_class(error: BaseException) -> str:
    name = type(error).__name__
    return name if name in SAFE_CLASSES else "OtherException"


def classify(stage: ChildStage | None) -> FailureCategory:
    if stage == ChildStage.HOST_COMPOSITION_STARTED:
        return FailureCategory.COMPOSITION_FAILURE
    if stage == ChildStage.CHILD_STARTED:
        return FailureCategory.BOOTSTRAP_FAILURE
    if stage in {
        ChildStage.HOST_COMPOSITION_COMPLETED,
        ChildStage.AGENT_CALL_STARTED,
        ChildStage.PAYLOAD_GUARD_STARTED,
        ChildStage.PAYLOAD_GUARD_COMPLETED,
    }:
        return FailureCategory.PRE_DISPATCH_AGENT_FAILURE
    # No adapter/HTTP boundary is observed here. Never infer transport failure
    # or absence of dispatch from an exception after governed runtime entry.
    return FailureCategory.UNKNOWN_CHILD_FAILURE


@dataclass
class ChildDiagnostics:
    stage: ChildStage | None = None
    failure: FailureCategory | None = None
    exception_class: str | None = None
    ipc: IPCStatus = IPCStatus.NO_ENVELOPE
    exitcode: int | None = None
    cleanup: Cleanup = Cleanup.NONE
    # PARSER-DIAGNOSTICS-1: closed labels for an Agent-rejected reply, if any.
    output: OutputDiagnosis | None = None

    def record(self) -> dict[str, Any]:
        record = {
            "child_stage": self.stage.value if self.stage else None,
            "child_failure_category": self.failure.value if self.failure else None,
            "exception_class": self.exception_class,
            "ipc_status": self.ipc.value,
            "child_exit_code": self.exitcode,
            "process_exit_observed": self.exitcode is not None,
            "cleanup_action": self.cleanup.value,
            "model_dispatch": "NOT_OBSERVED",
            "http_request": "NOT_OBSERVED",
            "provider_acceptance": "UNKNOWN",
        }
        if self.output is not None:
            record.update(self.output.record())
        return record
