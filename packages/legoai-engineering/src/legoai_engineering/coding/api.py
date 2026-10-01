"""One governed coding invocation returns M4 data, never applies it."""

import json
from dataclasses import dataclass, field
from typing import Protocol

from legoai.execution.agent.ports import AgentRequest, AgentResult, AgentRuntimePort
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.kernel.context import TenantContext

from legoai_engineering._json_document import json_document
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
    under an existing parent, UPDATE means exact acquired text. Raise a safe
    EvidenceAcquisitionError on failure; never return a partial bundle.
    """

    async def acquire(
        self, targets: tuple[CodingTarget, ...], tenant: TenantContext
    ) -> CodingEvidence: ...


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("coding object has unexpected fields")
    return value


def _array(value: object) -> list[object]:
    if type(value) is not list or len(value) > 8:
        raise ValueError("coding requires bounded arrays")
    return value


def _string(value: object) -> str:
    if type(value) is not str:
        raise TypeError("coding requires text")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate coding JSON key")
        result[key] = value
    return result


def _parse(output: str, evidence: CodingEvidence) -> CodingProposal:
    value: object = json.loads(json_document(output), object_pairs_hook=_unique_object)
    obj = _object(value, {"summary", "changes", "risks", "unknowns"})
    files = {file.target.path.value: file for file in evidence.files}
    changes = []
    reasons = []
    for raw in _array(obj["changes"]):
        change = _object(raw, {"path", "operation", "content", "reason"})
        path = RepositoryPath(_string(change["path"]))
        operation = FileChangeKind(_string(change["operation"]))
        current = files.get(path.value)
        if current is None or operation is not current.target.operation:
            raise ValueError("proposed path or operation is outside requested scope")
        changes.append(
            FileChange(path, operation, current.digest, _string(change["content"]))
        )
        reasons.append(_string(change["reason"]))
    return CodingProposal(
        RepositoryChangeSet(tuple(changes)),
        _string(obj["summary"]),
        tuple(reasons),
        tuple(_string(item) for item in _array(obj["risks"])),
        tuple(_string(item) for item in _array(obj["unknowns"])),
    )


@dataclass(frozen=True, slots=True)
class CodingAgent:
    evidence_reader: CodingEvidencePort = field(repr=False)
    agent_runtime: AgentRuntimePort = field(repr=False)

    async def propose(self, request: CodingRequest) -> CodingResult:
        if type(request) is not CodingRequest:
            raise TypeError("coding requires CodingRequest")
        try:
            evidence = await self.evidence_reader.acquire(
                request.targets, request.context.tenant_context
            )
        except EvidenceAcquisitionError as error:
            return CodingResult(
                CodingStatus.INVALID_REQUEST, request, None, None, None, error.reason
            )
        if type(evidence) is not CodingEvidence:
            raise TypeError("coding acquisition must return CodingEvidence")
        if {file.target for file in evidence.files} != set(request.targets):
            raise ValueError("coding evidence does not match requested targets")
        prompt = json.dumps(
            {
                "objective": request.objective,
                "constraints": request.constraints,
                "targets": [
                    {
                        "path": file.target.path.value,
                        "operation": file.target.operation.value,
                        "current_text": None
                        if file.current is None
                        else file.current.text,
                    }
                    for file in evidence.files
                ],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
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
            status = (
                CodingStatus.OUTPUT_INVALID
                if agent.status is AgentExecutionStatus.OUTPUT_INVALID
                else CodingStatus.MODEL_FAILURE
            )
            return CodingResult(status, request, evidence, agent, None)
        assert agent.output is not None
        try:
            proposal = _parse(agent.output, evidence)
            return CodingResult(
                CodingStatus.SUCCEEDED, request, evidence, agent, proposal
            )
        except ValueError, TypeError, RecursionError, WorkspaceError:
            return CodingResult(
                CodingStatus.OUTPUT_INVALID, request, evidence, agent, None
            )
