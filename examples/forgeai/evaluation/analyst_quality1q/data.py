"""Frozen CONTENT-DISCOVERY-1Q inputs: held-out cases, relevance oracle, partition.

Every supplied file belongs to exactly one oracle class: implementation (the
union of acceptable sets, which all contain the required files), context-only or
irrelevant. Relevance is not editability; nothing here creates a target. The
CONTENT-DISCOVERY-1 oracle is derived from its frozen read truth only.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from content_discovery1 import data as cd1
from legoai_engineering.analyst.api import repository_analyst_definition
from legoai_engineering.repository.values import RepositoryText
from legoai_engineering.repository.workspace import RepositoryPath

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
MANIFEST = "ecb80c9338c5912a023ca997ad960f539a3414ac04c0ee96e4bcb9ebea931e59"
PREDECLARATION = "planning/FORGEAI-CONTENT-DISCOVERY-ANALYST-QUALITY.md"
MARKER = "<!-- END 1Q PREDECLARATION -->"
EXPECTED = frozenset({"succeeded", "insufficient_evidence"})
HELDOUT_REPETITIONS = 3
CD1_REPETITIONS = 1
ANALYST_SOURCES = (
    "packages/legoai-engineering/src/legoai_engineering/analyst/api.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/values.py",
    "packages/legoai-engineering/src/legoai_engineering/analyst/authorized.py",
    "packages/legoai-engineering/src/legoai_engineering/_json_document.py",
)


def digest(path: Path) -> str:
    """SHA-256 of newline-normalized UTF-8 text (BOM ignored)."""
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8-sig"))
    )


def definition_fingerprint() -> str:
    """Identity of the Analyst behavior sent to the model (prompt and bounds)."""
    d = repository_analyst_definition()
    return hashlib.sha256(
        json.dumps(
            [
                d.agent_id.value,
                [
                    d.behavior_version.major,
                    d.behavior_version.minor,
                    d.behavior_version.patch,
                ],
                d.system_prompt,
                d.model_requirement.profile,
                d.output_contract.max_bytes,
                d.max_input_bytes,
                d.max_prompt_bytes,
            ]
        ).encode()
    ).hexdigest()


def predeclaration_digest() -> str:
    doc = (ROOT / PREDECLARATION).read_text(encoding="utf-8-sig")
    prefix, found, _ = doc.partition(MARKER)
    if not found:
        raise ValueError("predeclaration marker missing")
    return hashlib.sha256((prefix + MARKER + "\n").encode()).hexdigest()


@dataclass(frozen=True)
class Oracle:
    expected: str
    required: frozenset[str]
    acceptable: tuple[frozenset[str], ...]
    context: frozenset[str]
    irrelevant: frozenset[str]

    @property
    def implementation(self) -> frozenset[str]:
        return frozenset().union(*self.acceptable)


@dataclass(frozen=True)
class Case:
    id: str
    partition: str  # heldout | cd1_quality | cd1_probe
    klass: str
    question: str
    files: tuple[RepositoryText, ...]  # exactly the confirmed subset, sorted
    repository: frozenset[str]  # every path the synthetic repository holds
    oracle: Oracle
    repetitions: int

    @property
    def supplied(self) -> frozenset[str]:
        return frozenset(f.path for f in self.files)


def _strings(value: object) -> frozenset[str]:
    if not isinstance(value, list) or not all(isinstance(v, str) for v in value):
        raise ValueError("expected a list of strings")
    return frozenset(cast(list[str], value))


def validate(case: Case) -> None:
    o, supplied = case.oracle, case.supplied
    if o.expected not in EXPECTED or case.partition not in {
        "heldout",
        "cd1_quality",
        "cd1_probe",
    }:
        raise ValueError(f"{case.id}: invalid expectation or partition")
    if not 1 <= len(case.files) <= 8 or not supplied <= case.repository:
        raise ValueError(f"{case.id}: supplied files must be 1-8 repository files")
    for f in case.files:
        RepositoryPath(f.path)
        if len(f.text.encode()) > 8192:
            raise ValueError(f"{case.id}: file over the Analyst evidence bound")
    if sum(len(f.text.encode()) for f in case.files) > 24576:
        raise ValueError(f"{case.id}: evidence over the aggregate bound")
    if not 1 <= len(case.question.encode()) <= 2048:
        raise ValueError(f"{case.id}: question over bound")
    parts = (o.implementation, o.context, o.irrelevant)
    if (
        sum(len(p) for p in parts) != len(supplied)
        or frozenset().union(*parts) != supplied
    ):
        raise ValueError(f"{case.id}: oracle classes must partition supplied files")
    if o.expected == "succeeded":
        if not o.required or not o.acceptable:
            raise ValueError(f"{case.id}: answerable case needs required files")
        if any(not o.required <= s for s in o.acceptable):
            raise ValueError(f"{case.id}: every acceptable set contains the required")
    elif o.required or o.acceptable:
        raise ValueError(f"{case.id}: insufficient case has no required set")


def load_heldout() -> tuple[Case, ...]:
    top = read("heldout-v1.json")
    if top["namespace"] != "analyst-quality-1q-heldout" or top["revision"] != 1:
        raise ValueError("unexpected held-out namespace")
    cases = []
    for raw in cast(list[dict[str, object]], top["cases"]):
        files = cast(dict[str, list[str]], raw["files"])
        texts = tuple(
            RepositoryText(path, "\n".join(lines) + "\n")
            for path, lines in sorted(files.items())
        )
        oracle = cast(dict[str, object], raw["oracle"])
        case = Case(
            str(raw["id"]),
            "heldout",
            str(raw["class"]),
            str(raw["question"]),
            texts,
            frozenset(files),
            Oracle(
                str(oracle["expected"]),
                _strings(oracle["required"]),
                tuple(_strings(s) for s in cast(list[object], oracle["acceptable"])),
                _strings(oracle["context"]),
                _strings(oracle["irrelevant"]),
            ),
            HELDOUT_REPETITIONS,
        )
        validate(case)
        cases.append(case)
    if len(cases) != 24 or len({c.id for c in cases}) != 24:
        raise ValueError("expected 24 distinct held-out cases")
    return tuple(cases)


def _derived(source: cd1.Case) -> Oracle:
    """Relevance from CONTENT-DISCOVERY-1 read truth on the confirmed subset."""
    confirmed = frozenset(source.confirmed)
    union = frozenset().union(*source.read_sets) & confirmed
    if source.expected == "succeeded":
        required = source.required_reads & confirmed
        acceptable = tuple(
            sorted(
                {frozenset(s & confirmed) for s in source.read_sets} - {frozenset()},
                key=sorted,
            )
        )
        acceptable = tuple(s for s in acceptable if required <= s)
        implementation = frozenset().union(*acceptable)
        return Oracle(
            "succeeded",
            required,
            acceptable,
            frozenset(),
            confirmed - implementation,
        )
    return Oracle("insufficient_evidence", frozenset(), (), union, confirmed - union)


def load_cd1() -> tuple[Case, ...]:
    partition = read("partition-v1.json")
    quality = set(cast(list[str], partition["supporting_quality"]))
    probes = set(cast(list[str], partition["contract_probes"]))
    skipped = set(cast(list[str], partition["no_analyst_call"]))
    cases = []
    for source in cd1.load():
        if source.id in skipped:
            continue
        kind = "cd1_quality" if source.id in quality else "cd1_probe"
        if source.id not in quality | probes:
            raise ValueError(f"{source.id}: not partitioned")
        texts = tuple(f for f in source.files if f.path in set(source.confirmed))
        case = Case(
            source.id,
            kind,
            source.category,
            source.question,
            texts,
            frozenset(f.path for f in source.files),
            _derived(source),
            CD1_REPETITIONS,
        )
        validate(case)
        cases.append(case)
    return tuple(cases)


def plan() -> tuple[tuple[Case, int], ...]:
    """Every (case, repetition) call in frozen order; never changed by outcomes."""
    return tuple(
        (case, rep)
        for case in (*load_heldout(), *load_cd1())
        for rep in range(1, case.repetitions + 1)
    )


def freeze() -> dict[str, str]:
    """Verify every frozen input; returns the digests recorded in the condition."""
    cd1.freeze()
    manifest = read("manifest-v1.json")
    pre = read("preregistration-v1.json")
    if digest(HERE / "manifest-v1.json") != MANIFEST:
        raise ValueError("1Q manifest changed")
    for name in ("heldout-v1.json", "partition-v1.json", "thresholds-v1.json"):
        if digest(HERE / name) != manifest[name]:
            raise ValueError(f"{name} changed after freeze")
    if digest(HERE / "preregistration-v1.json") != manifest["preregistration-v1.json"]:
        raise ValueError("preregistration changed after freeze")
    if pre["predeclaration_digest"] != predeclaration_digest():
        raise ValueError("predeclaration changed after freeze")
    if pre["definition_fingerprint"] != definition_fingerprint():
        raise ValueError("RepositoryAnalyst definition changed")
    for path, expected in cast(dict[str, str], pre["analyst_sources"]).items():
        if digest(ROOT / path) != expected:
            raise ValueError(f"{path} changed")
    if digest(cd1.HERE / "manifest-v1.json") != pre["cd1_manifest"]:
        raise ValueError("CONTENT-DISCOVERY-1 manifest changed")
    return {
        "manifest": MANIFEST,
        "heldout": str(manifest["heldout-v1.json"]),
        "partition": str(manifest["partition-v1.json"]),
        "thresholds": str(manifest["thresholds-v1.json"]),
        "preregistration": str(manifest["preregistration-v1.json"]),
        "predeclaration": str(pre["predeclaration_digest"]),
        "cd1_manifest": str(pre["cd1_manifest"]),
    }


def thresholds() -> dict[str, object]:
    return read("thresholds-v1.json")
