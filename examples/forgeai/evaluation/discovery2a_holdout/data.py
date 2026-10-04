"""Frozen task/truth loading, separate from selectors and scoring."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from discovery2a.fixtures import Fixture, Truth, boolean, obj, strings, text, validate

HERE = Path(__file__).resolve().parent
DIFFICULTIES = ("EASY", "MEDIUM", "HARD", "PATH_ONLY_UNDERDETERMINED")
STRATA = frozenset(
    {
        "lexical",
        "source_tests",
        "similar_names",
        "different_concept",
        "architecture",
        "ambiguous",
        "create",
        "renamed_deprecated",
        "alternatives",
        "large_admitted",
        "decoy_heavy",
        "nested_feature",
        "package_names",
        "generic_names",
        "opaque_names",
        "nonmirroring_tests",
        "shared_interface",
    }
)
CLASSES = frozenset(
    {
        "none",
        "cross_directory_relationship",
        "misleading_naming",
        "semantic_relationship",
        "multi_file_relationship",
        "requirement_ambiguity",
        "create_need",
        "missing_identity",
        "multiple_valid_choices",
        "package_relationship",
        "context_relationship",
        "absent_behavior",
    }
)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def read(name: str) -> dict[str, object]:
    value: object = json.loads((HERE / name).read_text(encoding="utf-8-sig"))
    if not isinstance(value, dict):
        raise ValueError("invalid held-out object")
    return cast(dict[str, object], value)


def canonical(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


@dataclass(frozen=True)
class Case:
    fixture: Fixture
    difficulty: str
    stratum: str
    failure_class: str
    information_gap: str


def load() -> tuple[Case, ...]:
    data = obj(read("fixtures-v1.json"), {"namespace", "revision", "cases"})
    truth = obj(read("truth-v1.json"), {"revision", "cases"})
    if (
        data["namespace"] != "discovery2a_holdout_v1"
        or data["revision"] != 1
        or truth["revision"] != 1
    ):
        raise ValueError("invalid held-out identity")
    tasks, truths = data["cases"], truth["cases"]
    if (
        not isinstance(tasks, list)
        or not isinstance(truths, list)
        or len(tasks) != 36
        or len(truths) != 36
    ):
        raise ValueError("invalid workload size")
    result: list[Case] = []
    for task, oracle in zip(tasks, truths, strict=True):
        f = obj(
            task,
            {
                "id",
                "objective",
                "roots",
                "files",
                "stratum",
                "difficulty",
                "failure_class",
                "information_gap",
            },
        )
        t = obj(
            oracle,
            {
                "id",
                "required_paths",
                "acceptable_sets",
                "irrelevant_paths",
                "forbidden_paths",
                "expected_status",
                "manual_create",
            },
        )
        if f["id"] != t["id"] or not isinstance(t["acceptable_sets"], list):
            raise ValueError("mismatched ground truth")
        fixture = Fixture(
            text(f["id"]),
            text(f["stratum"]),
            text(f["objective"]),
            strings(f["roots"]),
            strings(f["files"]),
            (),
            Truth(
                frozenset(strings(t["required_paths"])),
                tuple(frozenset(strings(a)) for a in t["acceptable_sets"]),
                frozenset(strings(t["irrelevant_paths"])),
                frozenset(strings(t["forbidden_paths"])),
                text(t["expected_status"]),
                False,
                boolean(t["manual_create"]),
            ),
            "none",
        )
        case = Case(
            fixture,
            text(f["difficulty"]),
            text(f["stratum"]),
            text(f["failure_class"]),
            text(f["information_gap"]),
        )
        validate_case(case)
        result.append(case)
    if len({c.fixture.id for c in result}) != 36:
        raise ValueError("duplicate case identity")
    return tuple(result)


def validate_case(case: Case) -> None:
    f = case.fixture
    validate(f)
    if (
        case.difficulty not in DIFFICULTIES
        or case.stratum not in STRATA
        or case.failure_class not in CLASSES
    ):
        raise ValueError("invalid stratification")
    if case.information_gap not in {"visible", "intent", "create", "content"}:
        raise ValueError("invalid information gap")
    under = case.difficulty == "PATH_ONLY_UNDERDETERMINED"
    if under != (f.truth.expected == "insufficient_evidence") or under != (
        case.information_gap != "visible"
    ):
        raise ValueError("inconsistent difficulty/truth")
    if f.truth.manual_create != (case.information_gap == "create"):
        raise ValueError("inconsistent CREATE truth")
    if not f.truth.forbidden:
        raise ValueError("missing privacy challenge")
