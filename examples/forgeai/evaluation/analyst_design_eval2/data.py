"""Frozen revision-2 inputs and evaluator-only policy loading."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from legoai_engineering.analyst.sufficiency import (
    EvidenceRequest,
    EvidenceRequestKind,
    GoverningSourceExpectation,
)
from legoai_engineering.repository.workspace import RepositoryPath

from analyst_design_eval2.inputs import InputFacts

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-design-eval/2"
FREEZE_DIGEST = "210811368877d0227c00b2623fafaef069da3d9d1ac4a9553b80736140d76b93"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8"))
    )


def freeze() -> dict[str, str]:
    if digest(HERE / "freeze-v2.json") != FREEZE_DIGEST:
        raise ValueError("freeze manifest changed")
    pins = cast(dict[str, str], read("freeze-v2.json")["artifacts"])
    for name, value in pins.items():
        if digest(HERE / name) != value:
            raise ValueError("frozen artifact changed: " + name)
    return pins


@dataclass(frozen=True)
class Fixture:
    id: str
    partition: str
    category: str
    question: str
    files: dict[str, str]
    initial: list[str]
    addition: str
    clarification: str
    revised_question: str
    unrelated: str
    variants: list[str]
    manifest: str
    failure: str | None


@dataclass(frozen=True)
class Criterion:
    id: str
    kind: str
    path: str | None
    alternatives: tuple[str, ...]
    choices: tuple[str, ...]
    choice_groups: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Policy:
    required: tuple[Criterion, ...]
    allowed: tuple[Criterion, ...]
    forbidden_paths: tuple[str, ...]


def policy(raw: dict[str, object]) -> Policy:
    def criteria(key: str) -> tuple[Criterion, ...]:
        items = cast(list[dict[str, object]], raw[key])
        return tuple(
            Criterion(
                str(x["id"]),
                str(x["kind"]),
                cast(str | None, x["path"]),
                tuple(cast(list[str], x["alternatives"])),
                tuple(cast(list[str], x["choices"])),
                tuple(tuple(g) for g in cast(list[list[str]], x["choice_groups"])),
            )
            for x in items
        )

    result = Policy(
        criteria("required"),
        criteria("allowed"),
        tuple(cast(list[str], raw["forbidden_paths"])),
    )
    ids = [x.id for x in (*result.required, *result.allowed)]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate criteria")
    return result


@dataclass(frozen=True)
class Oracle:
    id: str
    initial: str
    expected: dict[str, str]
    governing: list[str]
    one_round_resolves: bool
    final_progression: dict[str, str]
    prohibited_progression: list[str]
    answerable: dict[str, bool]
    required_answer_evidence: list[str]
    facts: dict[str, str]
    critical: bool
    expected_failure: str | None
    rationale: dict[str, str]
    request_policy: dict[str, dict[str, object]]
    intervention_action: str
    semantic_delta: str
    clarification_answers: list[str]

    def at(self, phase: str, variant: str) -> Policy:
        # Unrelated conditions use the unchanged initial policy.
        return policy(self.request_policy["final" if phase == "final" else "initial"])


def load() -> tuple[tuple[Fixture, Oracle], ...]:
    freeze()
    fs = read("fixtures-v2.json")
    os = read("oracle-v2.json")
    if fs["revision"] != 2 or os["revision"] != 2:
        raise ValueError("wrong revision")
    result = []
    for f, o in zip(
        cast(list[dict[str, object]], fs["cases"]),
        cast(list[dict[str, object]], os["cases"]),
        strict=True,
    ):
        fixture = Fixture(**f)  # type: ignore[arg-type]
        oracle = Oracle(**o)  # type: ignore[arg-type]
        if fixture.id != oracle.id or set(fixture.variants) != set(oracle.expected):
            raise ValueError("case mismatch")
        for phase in ("initial", "final"):
            oracle.at(phase, "initial")
        result.append((fixture, oracle))
    if len(result) != 32 or len({f.id for f, o in result}) != 32:
        raise ValueError("case membership")
    return tuple(result)


def input_facts(case: str) -> InputFacts:
    # Deliberately reads no oracle, category, future intervention or fixture map.
    raw = cast(dict[str, dict[str, object]], read("inputs-v2.json")["cases"])[case]
    if set(raw) != {
        "question",
        "selected_paths",
        "expectations",
        "clarifications",
        "unknowns",
    }:
        raise ValueError("unexpected input facts")
    expectations = []
    origins = []
    for item in cast(list[dict[str, object]], raw["expectations"]):
        r = cast(dict[str, object], item["request"])
        req = EvidenceRequest(
            EvidenceRequestKind(str(r["kind"])),
            str(r["description"]),
            None if r["path"] is None else RepositoryPath(str(r["path"])),
            tuple(cast(list[str], r["choices"])),
        )
        expectations.append(
            GoverningSourceExpectation(
                str(item["key"]),
                req,
                tuple(
                    RepositoryPath(p) for p in cast(list[str], item["supplied_paths"])
                ),
            )
        )
        origins.append(str(item["provenance"]))
    if raw["clarifications"]:
        raise ValueError("no oracle clarification declarations allowed")
    return InputFacts(
        str(raw["question"]),
        tuple(cast(list[str], raw["selected_paths"])),
        tuple(expectations),
        tuple(origins),
        tuple(cast(list[str], raw["unknowns"])),
    )
