"""One governed M7 invocation over explicitly supplied review material."""

import json
from dataclasses import dataclass, field

from legoai.execution.agent.ports import AgentRequest, AgentResult, AgentRuntimePort
from legoai.execution.agent.values import AgentExecutionStatus

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


def _object(value: object, fields: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != fields:
        raise ValueError("review object has unexpected fields")
    return value


def _array(value: object) -> list[object]:
    if type(value) is not list or len(value) > 8:
        raise ValueError("review requires arrays of at most eight items")
    return value


def _string(value: object) -> str:
    if type(value) is not str:
        raise TypeError("review requires text")
    return value


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate review JSON key")
        result[key] = value
    return result


def _parse(output: str) -> Review:
    value: object = json.loads(output, object_pairs_hook=_unique_object)
    obj = _object(value, {"decision", "summary", "findings", "risks", "unknowns"})
    findings = []
    for item in _array(obj["findings"]):
        finding = _object(
            item,
            {"category", "severity", "message", "evidence_refs", "required_action"},
        )
        action = finding["required_action"]
        findings.append(
            ReviewFinding(
                FindingCategory(_string(finding["category"])),
                FindingSeverity(_string(finding["severity"])),
                _string(finding["message"]),
                tuple(_string(ref) for ref in _array(finding["evidence_refs"])),
                None if action is None else _string(action),
            )
        )
    return Review(
        ReviewDecision(_string(obj["decision"])),
        _string(obj["summary"]),
        tuple(findings),
        tuple(_string(risk) for risk in _array(obj["risks"])),
        tuple(_string(unknown) for unknown in _array(obj["unknowns"])),
    )


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
            status = (
                ReviewStatus.OUTPUT_INVALID
                if agent.status is AgentExecutionStatus.OUTPUT_INVALID
                else ReviewStatus.MODEL_FAILURE
            )
            return ReviewResult(status, request, agent, None)
        assert agent.output is not None
        try:
            return ReviewResult(
                ReviewStatus.COMPLETED, request, agent, _parse(agent.output)
            )
        except ValueError, TypeError, RecursionError:
            return ReviewResult(ReviewStatus.OUTPUT_INVALID, request, agent, None)
