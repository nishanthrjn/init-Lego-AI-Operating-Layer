"""Deterministic literal inspection, with no external effects or runtime wiring."""

from legoai_engineering.repository.values import (
    InspectionRequest,
    InspectionResult,
    RepositoryMatch,
)


def inspect_text(request: InspectionRequest) -> InspectionResult:
    """Return first occurrence per matching LF-delimited line in path order.

    Case-sensitive, no normalization/regex. CR before LF stays in the line;
    Unicode separators other than LF do not introduce a new line. Finite input
    and result bounds cap work; there is no I/O timeout or retry machinery.
    Application admission, input disclosure and resource policy remain external.
    """
    if type(request) is not InspectionRequest:
        raise TypeError("inspection requires InspectionRequest")
    matches: list[RepositoryMatch] = []
    for item in sorted(request.files, key=lambda entry: entry.path):
        for number, line in enumerate(item.text.split("\n"), start=1):
            column = line.find(request.query)
            if column < 0:
                continue
            if len(matches) == request.max_matches:
                return InspectionResult(tuple(matches), truncated=True)
            matches.append(RepositoryMatch(item.path, number, column + 1))
    return InspectionResult(tuple(matches), truncated=False)
