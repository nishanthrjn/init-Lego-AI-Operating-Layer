"""One governed coding invocation returns M4 data, never applies it."""

import json
from dataclasses import dataclass, field
from typing import Protocol

from legoai.execution.agent.ports import AgentRequest, AgentResult, AgentRuntimePort
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.kernel.context import TenantContext

from legoai_engineering._json_document import json_document
from legoai_engineering.agent_output import (
    OutputDiagnostic,
    OutputRejected,
    OutputRejection,
)
from legoai_engineering.analyst.values import (
    AcquisitionFailure,
    EvidenceAcquisitionError,
)
from legoai_engineering.coding.definition import coding_definition
from legoai_engineering.coding.values import (
    CodingEvidence,
    CodingProposal,
    CodingRequest,
    CodingResult,
    CodingStatus,
    CodingTarget,
)
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
)
from legoai_engineering.repository.workspace import RepositoryPath


class CodingEvidencePort(Protocol):
    """Trusted bound acquisition; authorize reads and configured Model disclosure.

    Return exactly the requested targets, sorted; CREATE means observed absence
    under an existing parent, UPDATE means exact acquired text. Return exactly
    the requested read-only references (None when there are none); they are
    disclosure only, never write scope. Raise a safe EvidenceAcquisitionError
    on failure; never return a partial bundle.
    """

    async def acquire(
        self,
        targets: tuple[CodingTarget, ...],
        tenant: TenantContext,
        references: tuple[RepositoryPath, ...] = (),
    ) -> CodingEvidence: ...


def _at(where: str, name: str) -> str:
    return f"{where}.{name}" if where else name


def _object(value: object, fields: set[str], where: str) -> dict[str, object]:
    if type(value) is not dict:
        raise OutputRejected(OutputRejection.FIELD_TYPE_INVALID, where or None)
    missing = sorted(fields - set(value))
    if missing:
        raise OutputRejected(
            OutputRejection.REQUIRED_FIELD_MISSING, _at(where, missing[0])
        )
    if set(value) != fields:
        raise OutputRejected(OutputRejection.UNKNOWN_FIELD, where or None)
    return value


def _array(value: object, where: str) -> list[object]:
    if type(value) is not list:
        raise OutputRejected(OutputRejection.FIELD_TYPE_INVALID, where)
    if len(value) > 8:
        raise OutputRejected(OutputRejection.ARRAY_BOUNDS_EXCEEDED, where)
    return value


def _string(value: object, where: str) -> str:
    if type(value) is not str:
        raise OutputRejected(OutputRejection.FIELD_TYPE_INVALID, where)
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise OutputRejected(OutputRejection.DUPLICATE_FIELD)
        result[key] = value
    return result


def _parse(output: str, evidence: CodingEvidence) -> CodingProposal:
    """Same checks and order as before; each rejection names where it failed."""
    try:
        value: object = json.loads(
            json_document(output), object_pairs_hook=_unique_object
        )
    except OutputRejected:
        raise
    except ValueError, RecursionError:
        raise OutputRejected(OutputRejection.JSON_DOCUMENT_INVALID) from None
    obj = _object(value, {"summary", "changes", "risks", "unknowns"}, "")
    files = {file.target.path.value: file for file in evidence.files}
    changes = []
    reasons = []
    for index, raw in enumerate(_array(obj["changes"], "changes")):
        where = f"changes[{index}]"
        change = _object(raw, {"path", "operation", "content", "reason"}, where)
        try:
            path = RepositoryPath(_string(change["path"], _at(where, "path")))
        except WorkspaceError:
            raise OutputRejected(
                OutputRejection.PATH_INVALID, _at(where, "path")
            ) from None
        text = _string(change["operation"], _at(where, "operation"))
        try:
            operation = FileChangeKind(text)
        except ValueError:
            raise OutputRejected(
                OutputRejection.ENUM_INVALID, _at(where, "operation")
            ) from None
        current = files.get(path.value)
        if current is None or operation is not current.target.operation:
            raise OutputRejected(OutputRejection.PATH_OUT_OF_SCOPE, where)
        content = _string(change["content"], _at(where, "content"))
        try:
            changes.append(FileChange(path, operation, current.digest, content))
        except ValueError, TypeError:
            raise OutputRejected(OutputRejection.VALUE_INVALID, where) from None
        reasons.append(_string(change["reason"], _at(where, "reason")))
    try:
        changeset = RepositoryChangeSet(tuple(changes))
    except ValueError, TypeError:
        raise OutputRejected(OutputRejection.VALUE_INVALID, "changes") from None
    summary = _string(obj["summary"], "summary")
    risks = tuple(_string(item, "risks") for item in _array(obj["risks"], "risks"))
    unknowns = tuple(
        _string(item, "unknowns") for item in _array(obj["unknowns"], "unknowns")
    )
    try:
        return CodingProposal(changeset, summary, tuple(reasons), risks, unknowns)
    except ValueError, TypeError:
        raise OutputRejected(OutputRejection.VALUE_INVALID, "proposal") from None


@dataclass(frozen=True, slots=True)
class CodingAgent:
    evidence_reader: CodingEvidencePort = field(repr=False)
    agent_runtime: AgentRuntimePort = field(repr=False)

    async def propose(self, request: CodingRequest) -> CodingResult:
        if type(request) is not CodingRequest:
            raise TypeError("coding requires CodingRequest")
        try:
            evidence = await self.evidence_reader.acquire(
                request.targets, request.context.tenant_context, request.references
            )
        except EvidenceAcquisitionError as error:
            return CodingResult(
                CodingStatus.INVALID_REQUEST, request, None, None, None, error.reason
            )
        if type(evidence) is not CodingEvidence:
            raise TypeError("coding acquisition must return CodingEvidence")
        if {file.target for file in evidence.files} != set(request.targets):
            raise ValueError("coding evidence does not match requested targets")
        if set(evidence.reference_paths) != set(request.references):
            raise ValueError("coding evidence does not match requested references")
        payload: dict[str, object] = {
            "objective": request.objective,
            "constraints": request.constraints,
            "targets": [
                {
                    "path": file.target.path.value,
                    "operation": file.target.operation.value,
                    "current_text": None if file.current is None else file.current.text,
                }
                for file in evidence.files
            ],
        }
        if evidence.references is not None:
            # Separate key, sorted by path: data to learn from, never targets.
            payload["read_only_context"] = [
                {"path": text.path, "text": text.text}
                for text in evidence.references.files
            ]
        prompt = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        definition = coding_definition()
        if len(prompt.encode("utf-8")) > definition.max_input_bytes:
            return CodingResult(
                CodingStatus.INVALID_REQUEST,
                request,
                evidence,
                None,
                None,
                AcquisitionFailure.BUDGET,
            )
        agent = await self.agent_runtime.run(
            definition, AgentRequest(request.context, prompt)
        )
        if type(agent) is not AgentResult:
            raise TypeError("coding runtime must return AgentResult")
        if (
            agent.definition != definition
            or agent.execution_id != request.context.execution_id
        ):
            raise ValueError("coding runtime returned unrelated attribution")
        if agent.status is not AgentExecutionStatus.SUCCEEDED:
            if agent.status is AgentExecutionStatus.OUTPUT_INVALID:
                contract = OutputDiagnostic(OutputRejection.OUTPUT_CONTRACT)
                return CodingResult(
                    CodingStatus.OUTPUT_INVALID,
                    request,
                    evidence,
                    agent,
                    None,
                    diagnostic=contract,
                )
            return CodingResult(
                CodingStatus.MODEL_FAILURE, request, evidence, agent, None
            )
        assert agent.output is not None
        try:
            proposal = _parse(agent.output, evidence)
            return CodingResult(
                CodingStatus.SUCCEEDED, request, evidence, agent, proposal
            )
        except OutputRejected as error:
            diagnostic = error.diagnostic
        except ValueError, TypeError, RecursionError, WorkspaceError:
            diagnostic = OutputDiagnostic(OutputRejection.VALUE_INVALID)
        return CodingResult(
            CodingStatus.OUTPUT_INVALID,
            request,
            evidence,
            agent,
            None,
            diagnostic=diagnostic,
        )
