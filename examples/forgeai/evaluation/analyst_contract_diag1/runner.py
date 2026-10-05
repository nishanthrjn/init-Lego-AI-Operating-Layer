"""One diagnostic call on the unchanged CONTENT-DISCOVERY-1Q request path.

The governed host, evidence reader, request and Analyst are exactly 1Q's; the
only addition is in-memory diagnosis of the reply the Analyst already returned.
The reply is checked against the Analyst's own verdict and against 1Q's coarse
classifier, then dropped. No reply text leaves this function.
"""

import asyncio
import time
from datetime import UTC, datetime

from analyst_quality1q.classify import classify
from analyst_quality1q.data import Case
from analyst_quality1q.harness import host
from content_discovery1.stages import Workspace
from legoai_engineering.analyst.api import RepositoryAnalyst
from legoai_engineering.analyst.authorized import (
    REPOSITORY_READ_ACTION,
    AuthorizedRepositoryEvidence,
)
from legoai_engineering.analyst.values import (
    RepositoryAnalysisRequest,
    RepositoryAnalysisResult,
    RepositoryAnalysisStatus,
)
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_contract_diag1.diagnose import COARSE, Diagnosis, Stage, diagnose
from legoai.execution.agent.values import AgentExecutionStatus
from legoai.runtime.api import ModelBindingConfig, ModelPurpose


async def _analyze(case: Case, binding: ModelBindingConfig) -> RepositoryAnalysisResult:
    now = datetime.now(UTC)
    governed, reference = host(binding, now)
    paths = tuple(RepositoryPath(f.path) for f in case.files)
    reader = AuthorizedRepositoryEvidence(
        reference,
        Workspace(case.files),
        governed.security_context(
            reference, REPOSITORY_READ_ACTION, reference.instance
        ),
        governed.authorization,
        paths,
        lambda: now,
    )
    return await RepositoryAnalyst(reader, governed.agent_runtime()).analyze(
        RepositoryAnalysisRequest(
            case.question, paths, governed.model_execution(ModelPurpose.CHAT)
        )
    )


def reconcile(
    result: RepositoryAnalysisResult, case: Case
) -> tuple[Diagnosis, str | None, bool]:
    """(diagnosis, 1Q coarse category, coarse-consistent) for one result."""
    agent = result.agent_result
    if result.status is RepositoryAnalysisStatus.MODEL_FAILURE:
        return Diagnosis(Stage.MODEL_FAILURE, "none"), None, True
    if agent is not None and agent.status is AgentExecutionStatus.OUTPUT_INVALID:
        return Diagnosis(Stage.OUTPUT_CONTRACT_INVALID, "none"), None, True
    if agent is None or agent.output is None:
        return Diagnosis(Stage.CLASSIFIER_DISAGREEMENT, "none"), None, False
    diagnosis = diagnose(agent.output, case.supplied)
    coarse = classify(agent.output, case.supplied)[0].value
    runtime_valid = result.status.value in {"succeeded", "insufficient_evidence"}
    if (diagnosis.stage is Stage.VALID) != runtime_valid:
        diagnosis = Diagnosis(
            Stage.CLASSIFIER_DISAGREEMENT,
            diagnosis.representation,
            diagnosis.expected_field_count,
            diagnosis.actual_field_count,
            diagnosis.missing_required_fields,
            diagnosis.unexpected_field_count,
            diagnosis.field_types,
            diagnosis.status_value,
        )
    return diagnosis, coarse, COARSE[diagnosis.stage] == coarse


def run_call(
    case: Case, repetition: int, binding: ModelBindingConfig
) -> dict[str, object]:
    """One content-free diagnostic record."""
    started = time.perf_counter()
    result = asyncio.run(_analyze(case, binding))
    seconds = round(time.perf_counter() - started, 3)
    diagnosis, coarse, consistent = reconcile(result, case)
    return {
        "case": case.id,
        "partition": case.partition,
        "class": case.klass,
        "repetition": repetition,
        "runtime_status": result.status.value,
        **diagnosis.as_record(),
        "coarse_1q_category": coarse,
        "coarse_consistent": consistent,
        "seconds": seconds,
    }
