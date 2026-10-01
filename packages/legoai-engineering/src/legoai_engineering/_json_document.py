"""Private JSON document representation shared by engineering Agents (ADR-021).

An engineering Agent reply is either one raw JSON document or one Markdown
code fence, labelled `json` or unlabelled, that encloses it. This module only
recognizes that outer envelope and returns the document text. It never parses
JSON, builds domain values, searches for braces, repairs, strips any other
wrapper or retries; each Agent's existing parser and validators then run
unchanged on the returned text.

The input is provider-neutral reply text (already accepted by the Agent
runtime's output contract, which bounds the whole reply, fence included).
"""

_WHITESPACE = " \t\r\n"  # JSON whitespace
_FENCE = "```"
_OPENING_LINES = frozenset({_FENCE, _FENCE + "json"})


def json_document(reply: str) -> str:
    """The JSON document text of a reply; anything else is returned unchanged.

    A fenced reply, after trimming JSON whitespace, must be at least three LF
    separated lines: an opening line of exactly "```" or "```json", the
    document lines, and a closing line of exactly "```" (a CR ending a fence
    line is ignored). Every other reply, including any malformed fence, is
    returned unchanged, so the existing parser rejects it as before.
    """
    trimmed = reply.strip(_WHITESPACE)
    if not trimmed.startswith(_FENCE):
        return reply
    lines = trimmed.split("\n")
    if (
        len(lines) < 3
        or lines[0].removesuffix("\r") not in _OPENING_LINES
        or lines[-1] != _FENCE
    ):
        return reply
    return "\n".join(lines[1:-1])
