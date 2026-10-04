"""Three small path-only baselines. No oracle, I/O, contents or model dependency."""

import re
import unicodedata
from dataclasses import dataclass

from legoai_engineering.repository.structure import RepositoryStructure
from legoai_engineering.repository.workspace import WorkspaceEntryKind

METHODS = ("lexical", "path_score", "conservative")


def tokens(value: str) -> frozenset[str]:
    # Split camel case before casefold. NFC comparison only; paths stay exact.
    value = re.sub(r"([a-z])([A-Z])", r"\1 \2", value)
    return frozenset(
        re.findall(r"[^\W_]+", unicodedata.normalize("NFC", value).casefold())
    )


@dataclass(frozen=True)
class Selection:
    status: str
    candidates: tuple[str, ...]
    unknowns: tuple[str, ...] = ()


def accepted(result: Selection, structure: RepositoryStructure) -> bool:
    files = {
        e.path.value for e in structure.entries if e.kind is WorkspaceEntryKind.FILE
    }
    return (
        result.status in {"succeeded", "insufficient_evidence"}
        and len(result.candidates) <= 8
        and len(set(result.candidates)) == len(result.candidates)
        and set(result.candidates) <= files
        and len(result.unknowns) <= 8
        and all(
            type(u) is str and bool(u.strip()) and len(u.encode("utf-8")) <= 1024
            for u in result.unknowns
        )
        and (
            bool(result.candidates)
            if result.status == "succeeded"
            else bool(result.unknowns)
        )
    )


def select(objective: str, structure: RepositoryStructure, method: str) -> Selection:
    if method not in METHODS:
        raise ValueError("unknown baseline")
    words = tokens(objective)
    scored: list[tuple[int, str]] = []
    for entry in structure.entries:
        if entry.kind is not WorkspaceEntryKind.FILE:
            continue
        path = entry.path.value
        stem = path.rsplit("/", 1)[-1].rsplit(".", 1)[0]
        filename_matches = len(words & tokens(stem))
        score = (
            filename_matches
            if method == "lexical"
            else 2 * filename_matches + len(words & tokens(path))
        )
        if score:
            scored.append((score, path))
    scored.sort(key=lambda item: (-item[0], item[1]))
    if method == "conservative":
        if {"new", "file"} <= words or not scored:
            return Selection("insufficient_evidence", (), ("needs_clarification",))
        if len(scored) > 1 and scored[0][0] == scored[1][0]:
            return Selection("insufficient_evidence", (), ("tied_path_signal",))
        scored = scored[:1]
    result = (
        Selection("succeeded", tuple(p for _, p in scored[:8]))
        if scored
        else Selection("insufficient_evidence", (), ("no_path_signal",))
    )
    if not accepted(result, structure):
        raise ValueError("invalid baseline result")
    return result
