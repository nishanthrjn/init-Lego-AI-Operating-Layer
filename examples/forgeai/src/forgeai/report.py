"""Pure, bounded run projection; model text and infrastructure stay private."""

import json
from collections.abc import Mapping
from enum import Enum

from legoai_engineering.reviewer.values import FindingSeverity

from forgeai.domain import TaskResult

REPORT_SCHEMA = "forgeai-run-report/1"
MAX_REPORT_BYTES = 65536


class ModelBindingKind(Enum):
    REPLAY = "REPLAY"
    OLLAMA = "OLLAMA"
    OPENAI_COMPATIBLE_REMOTE = "OPENAI_COMPATIBLE_REMOTE"


class ModelQuality(Enum):
    NOT_APPLICABLE_REPLAY = "NOT_APPLICABLE_REPLAY"
    UNQUALIFIED = "UNQUALIFIED"


def model_quality(binding: ModelBindingKind) -> ModelQuality:
    if binding is ModelBindingKind.REPLAY:
        return ModelQuality.NOT_APPLICABLE_REPLAY
    return ModelQuality.UNQUALIFIED


def run_report(result: TaskResult, binding: ModelBindingKind) -> dict[str, object]:
    """Project explicit safe fields, mirroring the bounded pilot's derivations."""
    evidence = result.evidence
    attempts = []
    for item in evidence.attempts:
        reviewer = item.review
        attempts.append(
            {
                "number": item.number,
                "coding_status": item.coding_status.name
                if item.coding_status
                else None,
                "model_attempt": item.agent_status.name if item.agent_status else None,
                "model_effect": item.model_effect.name if item.model_effect else None,
                "proposal_valid": item.proposal is not None,
                "mutation_approval": item.approval,
                "changed_paths": [
                    {"path": change.path.value, "kind": change.kind.name}
                    for change in item.applied.applied
                ]
                if item.applied
                else [],
                "mutation_uncertain": item.uncertain is not None,
                "mutation_denied": item.mutation_denial is not None,
                "mutation_conflict": item.conflict is not None,
                "checks": [
                    {
                        "kind": check.request.kind.name,
                        "outcome": check.result.outcome.name if check.result else None,
                        "no_result": check.result is None,
                    }
                    for check in item.checks
                ],
                "review_status": reviewer.status.name if reviewer else None,
                "review_decision": (
                    item.review_decision.name if item.review_decision else None
                ),
                "blocking_findings": sum(
                    finding.severity is FindingSeverity.BLOCKING
                    for finding in reviewer.review.findings
                )
                if reviewer is not None and reviewer.review is not None
                else None,
            }
        )
    return {
        "schema": REPORT_SCHEMA,
        "run_id": evidence.run_id,
        "disposition": result.disposition.name,
        "failure": result.failure.name if result.failure else None,
        "model_binding": binding.value,
        "model_quality": model_quality(binding).value,
        "start_head": evidence.start.head.commit.value
        if evidence.start is not None and evidence.start.head.commit is not None
        else None,
        "context_confirmed": evidence.context_confirmed,
        "rework_used": evidence.reworked,
        "rework_trigger": evidence.rework_trigger.name
        if evidence.rework_trigger
        else None,
        "changes_retained": any(item.applied is not None for item in evidence.attempts),
        "repository_effect": (
            "UNKNOWN"
            if any(item.uncertain is not None for item in evidence.attempts)
            else "KNOWN"
            if any(item.applied is not None for item in evidence.attempts)
            else "NONE"
        ),
        "rollback_performed": False,
        "attempts": attempts,
        "limitations": list(evidence.limitations),
    }


def encode_report(report: Mapping[str, object]) -> str:
    encoded = json.dumps(
        report, sort_keys=True, ensure_ascii=True, separators=(",", ":")
    )
    if len(encoded.encode("utf-8")) > MAX_REPORT_BYTES:
        raise ValueError("run report exceeds byte bound")
    return encoded
