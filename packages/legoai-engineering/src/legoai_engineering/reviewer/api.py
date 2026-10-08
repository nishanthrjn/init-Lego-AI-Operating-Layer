"""One governed M7 invocation over explicitly supplied review material."""

import json
from dataclasses import dataclass, field
from enum import Enum

from legoai.execution.agent.ports import AgentRequest, AgentResult, AgentRuntimePort
from legoai.execution.agent.values import AgentExecutionStatus

from legoai_engineering._json_document import json_document
from legoai_engineering.agent_output import (
    OutputDiagnostic,
    OutputRejected,
    OutputRejection,
)
from legoai_engineering.reviewer.definition import reviewer_definition
from legoai_engineering.reviewer.values import (
    FindingCategory,
    FindingSeverity,
    Review,
    ReviewDecision,
    ReviewFinding,
    ReviewRequest,
    ReviewResult,
    ReviewStatus,
    SubmissionFailure,
)


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


def _enum[E: Enum](kind: type[E], value: object, where: str) -> E:
    try:
        return kind(_string(value, where))
    except OutputRejected:
        raise
    except ValueError:
        raise OutputRejected(OutputRejection.ENUM_INVALID, where) from None


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise OutputRejected(OutputRejection.DUPLICATE_FIELD)
        result[key] = value
    return result


def _parse(output: str) -> Review:
    """Same checks and order as before; each rejection names where it failed."""
    try:
        value: object = json.loads(
            json_document(output), object_pairs_hook=_unique_object
        )
    except OutputRejected:
        raise
    except ValueError, RecursionError:
        raise OutputRejected(OutputRejection.JSON_DOCUMENT_INVALID) from None
    obj = _object(value, {"decision", "summary", "findings", "risks", "unknowns"}, "")
    findings = []
    for index, item in enumerate(_array(obj["findings"], "findings")):
        where = f"findings[{index}]"
        finding = _object(
            item,
            {"category", "severity", "message", "evidence_refs", "required_action"},
            where,
        )
        category = _enum(FindingCategory, finding["category"], _at(where, "category"))
        severity = _enum(FindingSeverity, finding["severity"], _at(where, "severity"))
        message = _string(finding["message"], _at(where, "message"))
        refs = _at(where, "evidence_refs")
        references = tuple(
            _string(ref, refs) for ref in _array(finding["evidence_refs"], refs)
        )
        action = finding["required_action"]
        required = (
            None if action is None else _string(action, _at(where, "required_action"))
        )
        try:
            findings.append(
                ReviewFinding(category, severity, message, references, required)
            )
        except ValueError, TypeError:
            raise OutputRejected(OutputRejection.VALUE_INVALID, where) from None
    decision = _enum(ReviewDecision, obj["decision"], "decision")
    summary = _string(obj["summary"], "summary")
    risks = tuple(_string(risk, "risks") for risk in _array(obj["risks"], "risks"))
    unknowns = tuple(
        _string(item, "unknowns") for item in _array(obj["unknowns"], "unknowns")
    )
    try:
        return Review(decision, summary, tuple(findings), risks, unknowns)
    except ValueError, TypeError:
        raise OutputRejected(OutputRejection.VALUE_INVALID, "review") from None


@dataclass(frozen=True, slots=True)
class IndependentReviewer:
    """Trusted caller owns provenance/disclosure; runtime owns governed Chat.

    No acquisition, tools, mutation or authorization issuance. The fixed reviewer
    identity differs from the supplied producer; this is definition independence,
    not proof of separate models, principals or unbiased reasoning.
    """

    agent_runtime: AgentRuntimePort = field(repr=False)

    async def review(self, request: ReviewRequest) -> ReviewResult:
        if type(request) is not ReviewRequest:
            raise TypeError("reviewer requires ReviewRequest")
        definition = reviewer_definition()
        if request.producer == definition.agent_id:
            return ReviewResult(
                ReviewStatus.INVALID_SUBMISSION,
                request,
                None,
                None,
                SubmissionFailure.SELF_REVIEW,
            )
        prompt = json.dumps(
            {
                "objective": request.objective,
                "criteria": request.criteria,
                "proposal": {"material_id": "proposal", "text": request.proposal},
                "evidence": [
                    {"material_id": item.material_id, "text": item.text}
                    for item in sorted(
                        request.evidence, key=lambda item: item.material_id
                    )
                ],
            },
            ensure_ascii=False,
            separators=(",", ":"),
        )
        if len(prompt.encode("utf-8")) > definition.max_input_bytes:
            return ReviewResult(
                ReviewStatus.INVALID_SUBMISSION,
                request,
                None,
                None,
                SubmissionFailure.CONTEXT_BUDGET,
            )
        agent = await self.agent_runtime.run(
            definition, AgentRequest(request.context, prompt)
        )
        if type(agent) is not AgentResult:
            raise TypeError("review runtime must return AgentResult")
        if (
            agent.definition != definition
            or agent.execution_id != request.context.execution_id
        ):
            raise ValueError("runtime returned unrelated review attribution")
        if agent.status is not AgentExecutionStatus.SUCCEEDED:
            if agent.status is AgentExecutionStatus.OUTPUT_INVALID:
                contract = OutputDiagnostic(OutputRejection.OUTPUT_CONTRACT)
                return ReviewResult(
                    ReviewStatus.OUTPUT_INVALID, request, agent, None, None, contract
                )
            return ReviewResult(ReviewStatus.MODEL_FAILURE, request, agent, None)
        assert agent.output is not None
        try:
            review = _parse(agent.output)
        except OutputRejected as error:
            return ReviewResult(
                ReviewStatus.OUTPUT_INVALID,
                request,
                agent,
                None,
                None,
                error.diagnostic,
            )
        try:
            return ReviewResult(ReviewStatus.COMPLETED, request, agent, review)
        except ValueError, TypeError:
            # After a successful parse, the only remaining completed-review
            # check is that every finding cites supplied material.
            cited = OutputDiagnostic(
                OutputRejection.FINDING_REFERENCE_INVALID, "findings"
            )
            return ReviewResult(
                ReviewStatus.OUTPUT_INVALID, request, agent, None, None, cited
            )
