"""Frozen synthetic cases and strict truth checks; never acquire real repositories."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from legoai_engineering.repository.structure import (
    RepositoryStructure,
    RepositoryStructurePolicy,
    StructureError,
    StructureFailure,
)
from legoai_engineering.repository.workspace import (
    RepositoryPath,
    WorkspaceEntry,
    WorkspaceEntryKind,
)

CAUSES = frozenset(
    {
        "none",
        "lexical_ambiguity",
        "missing_semantic_relationship",
        "cross_directory_relationship",
        "requirement_ambiguity",
        "create_need",
        "absent_content",
        "misleading_naming",
        "multiple_valid_choices",
        "acquisition_limit",
    }
)


def obj(value: object, keys: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != keys:
        raise ValueError("invalid fixture object")
    return cast(dict[str, object], value)


def strings(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or any(type(v) is not str for v in value):
        raise ValueError("invalid fixture strings")
    result = tuple(cast(list[str], value))
    if len(set(result)) != len(result) or any(not v.strip() for v in result):
        raise ValueError("invalid fixture strings")
    return result


def text(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid fixture text")
    return value


def boolean(value: object) -> bool:
    if type(value) is not bool:
        raise ValueError("invalid fixture boolean")
    return value


@dataclass(frozen=True)
class Truth:
    required: frozenset[str]
    acceptable: tuple[frozenset[str], ...]
    irrelevant: frozenset[str]
    forbidden: frozenset[str]
    expected: str
    acquisition_blocked: bool
    manual_create: bool


@dataclass(frozen=True)
class Fixture:
    id: str
    category: str
    objective: str
    roots: tuple[str, ...]
    files: tuple[str, ...]
    excluded_subtrees: tuple[str, ...]
    truth: Truth
    failure_category: str

    def structure(self) -> RepositoryStructure:
        policy = RepositoryStructurePolicy(
            tuple(RepositoryPath(p) for p in self.roots),
            excluded_subtrees=tuple(RepositoryPath(p) for p in self.excluded_subtrees),
        )
        entries = {p: WorkspaceEntryKind.DIRECTORY for p in self.roots}
        for name in self.files:
            path = RepositoryPath(name)
            if policy.excludes(path):
                continue
            entries[name] = WorkspaceEntryKind.FILE
            parent = name.rpartition("/")[0]
            while parent not in self.roots:
                if not parent:
                    raise ValueError("fixture outside roots")
                entries[parent] = WorkspaceEntryKind.DIRECTORY
                parent = parent.rpartition("/")[0]
        return RepositoryStructure(
            policy,
            tuple(
                WorkspaceEntry(RepositoryPath(p), kind)
                for p, kind in sorted(entries.items())
            ),
        )


def load() -> tuple[Fixture, ...]:
    raw: object = json.loads(
        Path(__file__).with_name("fixtures-v1.json").read_text(encoding="utf-8")
    )
    top = obj(raw, {"namespace", "revision", "cases"})
    if (
        top["namespace"] != "forgeai-discovery-paths"
        or type(top["revision"]) is not int
        or top["revision"] != 1
    ):
        raise ValueError("unknown fixture revision")
    cases = top["cases"]
    if not isinstance(cases, list) or not cases:
        raise ValueError("missing fixtures")
    result = []
    for item in cases:
        c = obj(
            item,
            {
                "id",
                "category",
                "objective",
                "roots",
                "files",
                "excluded_subtrees",
                "truth",
                "failure_category",
            },
        )
        t = obj(
            c["truth"],
            {
                "required",
                "acceptable",
                "irrelevant",
                "forbidden",
                "expected",
                "acquisition_blocked",
                "manual_create",
            },
        )
        alternatives = t["acceptable"]
        if not isinstance(alternatives, list):
            raise ValueError("invalid alternatives")
        fixture = Fixture(
            text(c["id"]),
            text(c["category"]),
            text(c["objective"]),
            strings(c["roots"]),
            strings(c["files"]),
            strings(c["excluded_subtrees"]),
            Truth(
                frozenset(strings(t["required"])),
                tuple(frozenset(strings(a)) for a in alternatives),
                frozenset(strings(t["irrelevant"])),
                frozenset(strings(t["forbidden"])),
                text(t["expected"]),
                boolean(t["acquisition_blocked"]),
                boolean(t["manual_create"]),
            ),
            text(c["failure_category"]),
        )
        validate(fixture)
        result.append(fixture)
    if len({f.id for f in result}) != len(result):
        raise ValueError("duplicate fixture ID")
    return tuple(result)


def validate(f: Fixture) -> None:
    t = f.truth
    if f.failure_category not in CAUSES or not f.id.isalnum():
        raise ValueError("unknown category or fixture ID")
    if len(f.objective.encode("utf-8")) > 2048:
        raise ValueError("objective oversized")
    policy = RepositoryStructurePolicy(
        tuple(RepositoryPath(p) for p in f.roots),
        excluded_subtrees=tuple(RepositoryPath(p) for p in f.excluded_subtrees),
    )
    for p in f.files:
        RepositoryPath(p)
        if not any(p.startswith(r + "/") for r in f.roots):
            raise ValueError("fixture outside roots")
    if len({p.casefold() for p in f.files}) != len(f.files):
        raise ValueError("duplicate fixture file")
    forbidden = frozenset(p for p in f.files if policy.excludes(RepositoryPath(p)))
    if t.forbidden != forbidden:
        raise ValueError("forbidden truth differs from disclosure policy")
    if t.expected not in {"succeeded", "insufficient_evidence"} or bool(
        t.acceptable
    ) != (t.expected == "succeeded"):
        raise ValueError("inconsistent expected outcome")
    if len(set(t.acceptable)) != len(t.acceptable):
        raise ValueError("duplicate acceptable sets")
    relevant = frozenset().union(*t.acceptable)
    if any(not a or len(a) > 8 or not t.required <= a for a in t.acceptable):
        raise ValueError("invalid acceptable set")
    if (
        not t.required <= relevant
        or relevant & forbidden
        or not relevant <= set(f.files)
    ):
        raise ValueError("invalid relevant truth")
    if t.irrelevant != set(f.files) - relevant - forbidden:
        raise ValueError("incomplete or overlapping truth")
    if t.manual_create and (t.acceptable or t.required or t.acquisition_blocked):
        raise ValueError("invalid CREATE truth")
    try:
        structure = f.structure()
    except StructureError as error:
        if (
            not t.acquisition_blocked
            or error.reason is not StructureFailure.STRUCTURE_LIMIT_EXCEEDED
        ):
            raise
    else:
        if t.acquisition_blocked:
            raise ValueError("expected acquisition refusal")
        files = {
            e.path.value for e in structure.entries if e.kind is WorkspaceEntryKind.FILE
        }
        if not relevant <= files or forbidden & files:
            raise ValueError("truth not disclosed")
