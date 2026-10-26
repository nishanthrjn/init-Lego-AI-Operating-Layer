"""Match consistent CRLF updates before approval; no I/O or authority."""

from collections.abc import Mapping

from legoai_engineering.coding.values import CodingProposal
from legoai_engineering.repository.mutation import (
    FileChange,
    FileChangeKind,
    RepositoryChangeSet,
)
from legoai_engineering.repository.workspace import RepositoryPath


def is_consistent_crlf(text: str | None) -> bool:
    """Require a CRLF and no lone CR or LF anywhere in the text."""
    if text is None or "\r\n" not in text:
        return False
    remainder = "".join(text.split("\r\n"))
    return "\r" not in remainder and "\n" not in remainder


def match_line_endings(
    proposal: CodingProposal, current: Mapping[RepositoryPath, str | None]
) -> CodingProposal:
    """Return a validated conversion, or the entire original on bound failure."""
    changes: list[FileChange] = []
    try:
        for change in proposal.changeset.changes:
            before = current.get(change.path)
            text = change.text
            if (
                change.kind is FileChangeKind.UPDATE
                and is_consistent_crlf(before)
                and text is not None
                and "\r" not in text
            ):
                text = "\r\n".join(text.split("\n"))
            changes.append(FileChange(change.path, change.kind, change.expected, text))
        converted = CodingProposal(
            RepositoryChangeSet(tuple(changes)),
            proposal.summary,
            proposal.reasons,
            proposal.risks,
            proposal.unknowns,
        )
    except ValueError, TypeError:
        return proposal
    return proposal if converted == proposal else converted
