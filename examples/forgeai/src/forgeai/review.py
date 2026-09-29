"""Deterministic review material for the independent reviewer (ForgeAI-2).

Pure rendering of application-owned evidence into the existing M8.2 values.
Nothing is truncated or summarized by a model: text that does not fit the
reviewer contract raises ValueError and the run reports a review-input
failure. Git state is never rendered; it is operator evidence only.
"""

from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.workspace import RepositoryPath
from legoai_engineering.reviewer.values import ReviewMaterial

from forgeai.domain import CheckRecord

CHECKS_MATERIAL = "checks"


def material_ids(
    paths: tuple[RepositoryPath, ...],
) -> tuple[tuple[str, RepositoryPath], ...]:
    """Stable application-owned IDs; they are labels, not repository paths."""
    return tuple((f"file-{index}", path) for index, path in enumerate(paths, 1))


def render_proposal(
    proposal: CodingProposal, materials: tuple[tuple[str, RepositoryPath], ...]
) -> str:
    """The Coding Agent's validated proposal as bounded deterministic text."""
    by_path = {path: material for material, path in materials}
    lines = [
        "Coding Agent proposal, rendered by ForgeAI from the validated proposal. "
        "Final file contents are supplied as the listed materials.",
        f"Summary: {proposal.summary}",
        "Changes:",
    ]
    for change, reason in zip(
        proposal.changeset.changes, proposal.reasons, strict=True
    ):
        lines.append(
            f"- {change.kind.value} {change.path.value} "
            f"(material {by_path[change.path]}): {reason}"
        )
    lines.append("Risks: " + ("; ".join(proposal.risks) or "none stated"))
    lines.append("Unknowns: " + ("; ".join(proposal.unknowns) or "none stated"))
    return "\n".join(lines)


def checks_material(records: tuple[CheckRecord, ...]) -> ReviewMaterial:
    """Outcome summary of the deterministic sandboxed checks; no tool output."""
    lines = [
        "Deterministic check results recorded by ForgeAI (sandboxed tool "
        "observations, not model output). A pass is a contained observation, "
        "not proof of correctness."
    ]
    for record in records:
        targets = ", ".join(path.value for path in record.request.targets)
        outcome = record.result.outcome.value if record.result else "not completed"
        lines.append(f"- {record.request.kind.value} on {targets}: {outcome}")
    return ReviewMaterial(CHECKS_MATERIAL, "\n".join(lines))


def file_material(material_id: str, path: RepositoryPath, text: str) -> ReviewMaterial:
    """Final content of one applied file, read through authorized reads."""
    return ReviewMaterial(
        material_id,
        f"Final content of {path.value} after the change was applied:\n{text}",
    )
