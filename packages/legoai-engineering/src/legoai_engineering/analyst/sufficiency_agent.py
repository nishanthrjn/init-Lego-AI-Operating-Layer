"""One governed assessment of an externally authorized current evidence bundle."""

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from legoai.execution.agent.ports import AgentRequest, AgentResult, AgentRuntimePort
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.execution.values import ExecutionContext
from legoai_engineering._json_document import json_document
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
    EvidenceSufficiencyAssessment,
    EvidenceSufficiencyError,
    EvidenceSufficiencyResult,
    SufficiencyDisposition,
    SufficiencyFailure,
)
from legoai_engineering.analyst.sufficiency_definition import (
    evidence_sufficiency_definition,
)
from legoai_engineering.repository.errors import WorkspaceError
from legoai_engineering.repository.workspace import RepositoryPath

__all__ = ["EvidenceSufficiencyAgent"]


def _request(request: EvidenceRequest) -> dict[str, object]:
    return {
        "kind": request.kind.value,
        "description": request.description,
        "path": request.path.value if request.path else None,
        "choices": request.choices,
    }


def _serialize(manifest: EvidenceManifest) -> str:
    return json.dumps(
        {
            "question": manifest.question,
            "files": [
                {"path": f.path, "text": f.text} for f in manifest.evidence.files
            ],
            "expectations": [
                {
                    "key": x.key,
                    "request": _request(x.request),
                    "supplied_paths": sorted(p.value for p in x.supplied_paths),
                }
                for x in sorted(manifest.expectations, key=lambda x: x.key)
            ],
            "clarifications": [
                {"key": x.key, "request": _request(x.request), "answer": x.answer}
                for x in sorted(manifest.clarifications, key=lambda x: x.key)
            ],
            "unknowns": sorted(manifest.unknowns),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )


def _object(value: object, keys: set[str]) -> dict[str, object]:
    if type(value) is not dict or set(value) != keys:
        raise ValueError("unexpected sufficiency fields")
    return value


def _array(value: object) -> list[object]:
    if type(value) is not list or len(value) > 8:
        raise ValueError("bounded array required")
    return value


def _string(value: object) -> str:
    if type(value) is not str:
        raise TypeError("text required")
    return value


def _unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def _parse(output: str, manifest: EvidenceManifest) -> EvidenceSufficiencyAssessment:
    obj = _object(
        json.loads(json_document(output), object_pairs_hook=_unique),
        {"disposition", "explanation", "governing_sources", "requests"},
    )
    requests = []
    for item in _array(obj["requests"]):
        r = _object(item, {"kind", "description", "path", "choices"})
        requests.append(
            EvidenceRequest(
                EvidenceRequestKind(_string(r["kind"])),
                _string(r["description"]),
                None if r["path"] is None else RepositoryPath(_string(r["path"])),
                tuple(_string(c) for c in _array(r["choices"])),
            )
        )
    return EvidenceSufficiencyAssessment(
        manifest,
        SufficiencyDisposition(_string(obj["disposition"])),
        _string(obj["explanation"]),
        tuple(RepositoryPath(_string(p)) for p in _array(obj["governing_sources"])),
        tuple(requests),
    )


@dataclass(frozen=True, slots=True)
class EvidenceSufficiencyAgent:
    """Caller owns read/disclosure authority and current in-memory manifest state.

    current_manifest must synchronously return the current trusted observation,
    without acquisition. Results remain advisory and require validation again at
    use. Unexpected runtime errors and cancellation propagate as in Core M7.
    """

    agent_runtime: AgentRuntimePort = field(repr=False)

    async def assess(
        self,
        context: ExecutionContext,
        manifest: EvidenceManifest,
        *,
        current_manifest: Callable[[], EvidenceManifest],
    ) -> EvidenceSufficiencyResult:
        if (
            type(context) is not ExecutionContext
            or type(manifest) is not EvidenceManifest
        ):
            raise TypeError("execution context and evidence manifest required")
        identity = manifest.identity()

        def is_current() -> bool:
            current = current_manifest()
            if type(current) is not EvidenceManifest:
                raise TypeError("current manifest required")
            return current.identity() == identity

        if not is_current():
            return EvidenceSufficiencyResult(
                failure=SufficiencyFailure.STALE_ASSESSMENT
            )
        definition = evidence_sufficiency_definition()
        prompt = _serialize(manifest)
        if len(prompt.encode("utf-8")) > definition.max_input_bytes:
            return EvidenceSufficiencyResult(
                failure=SufficiencyFailure.BUDGET_EXHAUSTED
            )
        agent = await self.agent_runtime.run(definition, AgentRequest(context, prompt))
        if type(agent) is not AgentResult:
            raise TypeError("runtime must return AgentResult")
        if agent.definition != definition or agent.execution_id != context.execution_id:
            raise ValueError("unrelated Agent attribution")
        if not is_current():
            return EvidenceSufficiencyResult(
                failure=SufficiencyFailure.STALE_ASSESSMENT
            )
        if agent.status is not AgentExecutionStatus.SUCCEEDED:
            return EvidenceSufficiencyResult(
                failure=(
                    SufficiencyFailure.INVALID_OUTPUT
                    if agent.status is AgentExecutionStatus.OUTPUT_INVALID
                    else SufficiencyFailure.MODEL_FAILURE
                )
            )
        assert agent.output is not None
        try:
            return EvidenceSufficiencyResult(assessment=_parse(agent.output, manifest))
        except EvidenceSufficiencyError as error:
            return EvidenceSufficiencyResult(failure=error.reason)
        except ValueError, TypeError, RecursionError, WorkspaceError:
            return EvidenceSufficiencyResult(failure=SufficiencyFailure.INVALID_OUTPUT)
