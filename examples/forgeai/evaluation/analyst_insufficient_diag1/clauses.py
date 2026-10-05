"""Clause refinement of insufficient_inconsistent and closed abstention classes.

Applied only after DIAG-1 has diagnosed the reply, so every earlier parser stage
(ADR-021 decode, JSON, field set, status, shapes, bounds) has already passed
whenever counts are taken. Only two integers leave this module; no text does.
"""

import json
from enum import StrEnum

from analyst_contract_diag1.diagnose import Diagnosis, Stage, representation


class Refined(StrEnum):
    FINDINGS_PRESENT = "insufficient_findings_present"
    UNKNOWNS_EMPTY = "insufficient_unknowns_empty"
    BOTH = "insufficient_findings_present_and_unknowns_empty"


class Abstention(StrEnum):
    VALID_ABSTENTION = "valid_abstention"
    INVALID_ABSTENTION = "invalid_abstention"
    VALID_SUCCESS = "valid_success"
    OTHER_INVALID = "other_invalid"


INSUFFICIENT = "insufficient_evidence"


def refine(findings: int, unknowns: int) -> Refined | None:
    """The clause(s) of the unchanged rule a reply violates; None if it holds."""
    if findings and not unknowns:
        return Refined.BOTH
    if findings:
        return Refined.FINDINGS_PRESENT
    if not unknowns:
        return Refined.UNKNOWNS_EMPTY
    return None


def abstention(stage: str, status: str | None) -> Abstention:
    if stage == Stage.INSUFFICIENT_INCONSISTENT:
        return Abstention.INVALID_ABSTENTION
    if stage == Stage.VALID:
        return (
            Abstention.VALID_ABSTENTION
            if status == INSUFFICIENT
            else Abstention.VALID_SUCCESS
        )
    return Abstention.OTHER_INVALID


def counts(reply: str) -> tuple[int, int]:
    """(findings, unknowns) of a reply already past every shape stage."""
    document, _ = representation(reply)
    value = json.loads(document)
    return len(value["findings"]), len(value["unknowns"])


def observe(diagnosis: Diagnosis, reply: str | None) -> dict[str, object]:
    """Closed facts for one reply; counts only for insufficient-evidence replies
    that reached the insufficient rule (stage valid or insufficient_inconsistent).
    """
    stage = diagnosis.stage
    status = diagnosis.status_value
    record: dict[str, object] = {
        "actual_status": status if status in {"succeeded", INSUFFICIENT} else None,
        "abstention": abstention(stage, status).value,
        "findings_count": None,
        "unknowns_count": None,
        "findings_present": None,
        "unknowns_empty": None,
        "refined": None,
        "refinement_consistent": True,
    }
    reached = stage in {Stage.VALID, Stage.INSUFFICIENT_INCONSISTENT}
    if reached and status == INSUFFICIENT and reply is not None:
        findings, unknowns = counts(reply)
        refined = refine(findings, unknowns)
        record.update(
            findings_count=findings,
            unknowns_count=unknowns,
            findings_present=findings > 0,
            unknowns_empty=unknowns == 0,
            refined=None if refined is None else refined.value,
            refinement_consistent=(refined is not None)
            == (stage == Stage.INSUFFICIENT_INCONSISTENT),
        )
    return record
