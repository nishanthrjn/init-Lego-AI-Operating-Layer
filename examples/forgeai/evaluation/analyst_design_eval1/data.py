"""Separate frozen fixture/oracle ownership and a strict disclosure projection."""

import hashlib
import json
from dataclasses import dataclass, fields
from pathlib import Path
from typing import cast

from legoai_engineering.analyst.sufficiency import EvidenceManifest
from legoai_engineering.repository.workspace import RepositoryPath

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-design-eval/1"
FREEZE_DIGEST = "34073e24ad50142fac7f6636a276bdb0a16b03fc3f147ad4833a034d6c01ad38"
DISPOSITIONS = {"sufficient", "missing_governing_evidence", "unresolved_ambiguity"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8"))
    )


def freeze() -> dict[str, str]:
    if digest(HERE / "freeze-v1.json") != FREEZE_DIGEST:
        raise ValueError("freeze manifest changed")
    pinned = cast(dict[str, str], read("freeze-v1.json")["artifacts"])
    for name, expected in pinned.items():
        if digest(HERE / name) != expected:
            raise ValueError("frozen artifact changed: " + name)
    return pinned


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
class Oracle:
    id: str
    initial: str
    expected: dict[str, str]
    governing: list[str]
    request_kind: str
    request_path: str | None
    source_role: str
    clarification_required: bool
    one_round_resolves: bool
    final_progression: dict[str, str]
    prohibited_progression: list[str]
    answerable: dict[str, bool]
    required_answer_evidence: list[str]
    facts: dict[str, str]
    critical: bool
    expected_failure: str | None
    rationale: dict[str, str]


def load() -> tuple[tuple[Fixture, Oracle], ...]:
    freeze()
    fixtures, oracles = read("fixtures-v1.json"), read("oracle-v1.json")
    if (
        fixtures["namespace"],
        fixtures["revision"],
        oracles["namespace"],
        oracles["revision"],
    ) != (
        "forgeai-analyst-design-fixtures",
        1,
        "forgeai-analyst-design-oracle",
        1,
    ):
        raise ValueError("condition revisions mismatch")
    pairs = []
    raw_f = cast(list[dict[str, object]], fixtures["cases"])
    raw_o = cast(list[dict[str, object]], oracles["cases"])
    if len(raw_f) != 32 or len(raw_o) != 32:
        raise ValueError("case count changed")
    for f, o in zip(raw_f, raw_o, strict=True):
        if set(f) != {x.name for x in fields(Fixture)} or set(o) != {
            x.name for x in fields(Oracle)
        }:
            raise ValueError("unexpected fixture/oracle fields")
        fixture = Fixture(**f)  # type: ignore[arg-type]
        oracle = Oracle(**o)  # type: ignore[arg-type]
        validate(fixture, oracle)
        pairs.append((fixture, oracle))
    if len({f.id for f, _ in pairs}) != 32:
        raise ValueError("duplicate case identity")
    return tuple(pairs)


def validate(f: Fixture, o: Oracle) -> None:
    if f.id != o.id or f.partition not in {"heldout", "regression"}:
        raise ValueError("case attribution mismatch")
    if o.initial not in DISPOSITIONS or set(o.expected) != set(f.variants):
        raise ValueError("invalid oracle disposition/variants")
    if not 1 <= len(f.initial) <= 8 or not set(f.initial) <= set(f.files):
        raise ValueError("invalid initial evidence")
    if not o.governing or not set(o.governing) <= set(f.files):
        raise ValueError("invalid governing evidence")
    for path, text in f.files.items():
        RepositoryPath(path)
        if type(text) is not str or len(text.encode()) > 8192:
            raise ValueError("invalid bounded fixture content")
    if not f.question.strip() or len(f.question.encode()) > 2048:
        raise ValueError("invalid question")
    if set(o.rationale) != {
        "supplied_support",
        "missing_or_ambiguous",
        "unrelated_control",
        "intervention",
    } or not all(o.rationale.values()):
        raise ValueError("missing oracle rationale")
    for variant, expected in o.expected.items():
        answerable = expected == "sufficient" and f.failure is None
        if expected not in DISPOSITIONS or o.answerable[variant] != answerable:
            raise ValueError("inconsistent answerability")
        if o.final_progression[variant] != (
            "eligible_for_analysis" if answerable else "stopped"
        ):
            raise ValueError("inconsistent progression oracle")
        if (variant in o.prohibited_progression) == answerable:
            raise ValueError("inconsistent prohibited progression")
    if f.partition == "heldout" and f.category in {
        "named_missing",
        "role_missing",
        "ambiguity",
    }:
        if f.variants != ["initial", "resolved", "unrelated"] or o.expected != {
            "initial": o.initial,
            "resolved": "sufficient",
            "unrelated": o.initial,
        }:
            raise ValueError("broken changed-evidence pair")


def model_input(manifest: EvidenceManifest) -> dict[str, object]:
    """Only current observations. Never accepts Fixture, Oracle or repository map.

    No prompt is created. This is an allowlisted projection for future consumers.
    """
    if type(manifest) is not EvidenceManifest:
        raise TypeError("current manifest required; oracle input forbidden")
    return {
        "question": manifest.question,
        "files": [{"path": f.path, "text": f.text} for f in manifest.evidence.files],
        "clarifications": [
            {"question": c.request.description, "answer": c.answer}
            for c in manifest.clarifications
        ],
    }
