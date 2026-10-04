"""Frozen synthetic content and separate read/target truth."""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from discovery2a.fixtures import boolean, obj, strings, text
from legoai_engineering.repository.structure import RepositoryStructurePolicy
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST = "cbf5900d0633cf77cf29a83ce534054bad5db23842e8c095ff5f43b86f2e1fd6"


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8-sig"))
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def freeze() -> None:
    m, p = read("manifest-v1.json"), read("preregistration-v1.json")
    assert digest(HERE / "manifest-v1.json") == MANIFEST
    for filename, expected in (
        ("fixtures-v1.json", m["fixture_digest"]),
        ("preregistration-v1.json", m["preregistration_digest"]),
        ("thresholds-v1.json", p["threshold_digest"]),
    ):
        assert digest(HERE / filename) == expected, "frozen evaluation changed"
    for filename, expected in cast(dict[str, str], p["frozen_inputs"]).items():
        assert digest(ROOT / filename) == expected, "historical source/artifact changed"
    doc = (ROOT / "planning/FORGEAI-CONTENT-DISCOVERY-EVALUATION.md").read_text(
        encoding="utf-8-sig"
    )
    marker = "<!-- END CONTENT PREDECLARATION -->"
    prefix, found, _ = doc.partition(marker)
    assert (
        found
        and hashlib.sha256((prefix + marker + "\n").encode()).hexdigest()
        == p["predeclaration_digest"]
    )


@dataclass(frozen=True)
class Case:
    id: str
    category: str
    origin: str | None
    question: str
    roots: tuple[str, ...]
    files: tuple[RepositoryText, ...]
    read_policy: tuple[str, ...]
    edit_policy: tuple[str, ...]
    mode: str
    confirmed: tuple[str, ...]
    required_reads: frozenset[str]
    read_sets: tuple[frozenset[str], ...]
    irrelevant_reads: frozenset[str]
    forbidden: frozenset[str]
    required_targets: frozenset[str]
    target_sets: tuple[frozenset[str], ...]
    expected: str
    create: bool
    replay_status: str
    replay_relevant: tuple[str, ...]
    final_confirmation: tuple[str, ...]


def sets(value: object) -> tuple[frozenset[str], ...]:
    if not isinstance(value, list):
        raise ValueError("invalid truth sets")
    return tuple(frozenset(strings(v)) for v in value)


def load() -> tuple[Case, ...]:
    top = obj(read("fixtures-v1.json"), {"namespace", "revision", "cases"})
    assert top["namespace"] == "content-discovery-1" and top["revision"] == 1
    result = []
    for raw in cast(list[object], top["cases"]):
        f = obj(
            raw,
            {
                "id",
                "category",
                "origin",
                "question",
                "roots",
                "files",
                "read_policy",
                "edit_policy",
                "confirmation",
                "read_truth",
                "target_truth",
                "replay",
                "final_confirmation",
            },
        )
        r = obj(f["read_truth"], {"required", "acceptable", "irrelevant", "forbidden"})
        t = obj(f["target_truth"], {"required", "acceptable", "expected", "create"})
        c = obj(f["confirmation"], {"mode", "paths"})
        replay = obj(f["replay"], {"status", "relevant"})
        files = cast(dict[str, str], f["files"])
        case = Case(
            text(f["id"]),
            text(f["category"]),
            None if f["origin"] is None else text(f["origin"]),
            text(f["question"]),
            strings(f["roots"]),
            tuple(RepositoryText(p, v) for p, v in sorted(files.items())),
            strings(f["read_policy"]),
            strings(f["edit_policy"]),
            text(c["mode"]),
            strings(c["paths"]),
            frozenset(strings(r["required"])),
            sets(r["acceptable"]),
            frozenset(strings(r["irrelevant"])),
            frozenset(strings(r["forbidden"])),
            frozenset(strings(t["required"])),
            sets(t["acceptable"]),
            text(t["expected"]),
            boolean(t["create"]),
            text(replay["status"]),
            strings(replay["relevant"]),
            strings(f["final_confirmation"]),
        )
        validate(case)
        result.append(case)
    assert len(result) == len({c.id for c in result}) == 20
    return tuple(result)


def validate(c: Case) -> None:
    policy = RepositoryStructurePolicy(tuple(RepositoryPath(p) for p in c.roots))
    all_paths = {f.path for f in c.files}
    excluded = {p for p in all_paths if policy.excludes(RepositoryPath(p))}
    allowed = all_paths - excluded
    assert excluded == c.forbidden and set(c.read_policy) == allowed
    assert set(c.edit_policy) <= allowed
    assert set(c.confirmed) <= allowed and len(c.confirmed) <= 8
    assert c.mode in {"all", "subset", "manual_add", "reject"}
    assert bool(c.confirmed) == (c.mode != "reject")
    assert c.required_reads <= allowed
    assert c.read_sets and all(
        c.required_reads <= s <= allowed and 1 <= len(s) <= 8 for s in c.read_sets
    )
    assert c.irrelevant_reads == allowed - frozenset().union(*c.read_sets)
    assert bool(c.target_sets) == (c.expected == "succeeded")
    assert all(
        c.required_targets <= s <= set(c.edit_policy) and 1 <= len(s) <= 8
        for s in c.target_sets
    )
    assert c.required_targets <= frozenset().union(*c.target_sets)
    assert set(c.final_confirmation) <= set(c.edit_policy) & set(c.confirmed)
    assert not c.create or not c.target_sets
    assert c.replay_status in {"succeeded", "insufficient_evidence"}
    assert set(c.replay_relevant) <= set(c.confirmed)
    assert len(c.question.encode()) <= 2048
    assert all(len(f.text.encode()) <= 8192 for f in c.files)
