"""Frozen revision-2 artifacts; revision-1 value types reused unchanged.

Model-visible facts come from inputs-s2.json only. Application-known
declarations use the existing GoverningSourceExpectation mechanism (provenance
`application_known_prerequisite`); none of the frozen 22 cases declares one.
"""

import hashlib
import json
from pathlib import Path
from typing import cast

from analyst_design_eval2.inputs import InputFacts
from analyst_sufficiency_safety_eval1.data import HISTORICAL, Case, Oracle, _oracle
from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    EvidenceRequest,
    EvidenceRequestKind,
    GoverningSourceExpectation,
)
from legoai_engineering.analyst.values import RepositoryEvidence
from legoai_engineering.repository.workspace import RepositoryPath

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-sufficiency-safety-eval/2"
REPORT = "forgeai-analyst-sufficiency-safety-report/2"
PROVENANCE = "sufficiency-safety-eval2-observation"
FREEZE_DIGEST = "8933352eec8a0033e62d1b8d17c8d75788b1925caea8e1be99d5f0e1958c3906"
CASE_COUNT = 22
__all__ = ["HISTORICAL", "Case", "Oracle"]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8"))
    )


def freeze() -> dict[str, str]:
    """Verify every frozen revision-2 artifact against freeze-s2.json."""
    if digest(HERE / "freeze-s2.json") != FREEZE_DIGEST:
        raise ValueError("safety freeze manifest changed")
    manifest = read("freeze-s2.json")
    if manifest["condition"] != CONDITION:
        raise ValueError("wrong safety condition")
    pins = cast(dict[str, str], manifest["artifacts"])
    for name, value in pins.items():
        if digest(HERE / name) != value:
            raise ValueError("frozen safety artifact changed: " + name)
    return pins


def gates() -> dict[str, object]:
    return read("gates-s2.json")


def load() -> tuple[tuple[Case, Oracle], ...]:
    freeze()
    fixtures = cast(list[dict[str, object]], read("fixtures-s2.json")["cases"])
    oracles = cast(list[dict[str, object]], read("oracle-s2.json")["cases"])
    result = []
    for f, o in zip(fixtures, oracles, strict=True):
        case = Case(str(f["id"]), dict(cast(dict[str, str], f["files"])))
        oracle = _oracle(o)
        if case.id != oracle.id:
            raise ValueError("case/oracle mismatch")
        result.append((case, oracle))
    ids = [c.id for c, _ in result]
    if (
        len(ids) != CASE_COUNT
        or len(set(ids)) != CASE_COUNT
        or ids != list(cast(list[str], gates()["gating_cases"]))
        or set(ids) & set(HISTORICAL)
    ):
        raise ValueError("safety case membership")
    return tuple(result)


def parse_facts(raw: dict[str, object]) -> InputFacts:
    """Model-visible facts, including application-known path declarations."""
    if set(raw) != {
        "question",
        "selected_paths",
        "expectations",
        "clarifications",
        "unknowns",
    }:
        raise ValueError("unexpected input facts")
    if raw["clarifications"] or raw["unknowns"]:
        raise ValueError("no clarification or unknown declarations allowed")
    expectations, origins = [], []
    for item in cast(list[dict[str, object]], raw["expectations"]):
        r = cast(dict[str, object], item["request"])
        if r["kind"] != "named_evidence" or item["provenance"] != (
            "application_known_prerequisite"
        ):
            raise ValueError("only application-known named declarations allowed")
        expectations.append(
            GoverningSourceExpectation(
                str(item["key"]),
                EvidenceRequest(
                    EvidenceRequestKind.NAMED_EVIDENCE,
                    str(r["description"]),
                    RepositoryPath(str(r["path"])),
                ),
            )
        )
        origins.append(str(item["provenance"]))
    return InputFacts(
        str(raw["question"]),
        tuple(cast(list[str], raw["selected_paths"])),
        tuple(expectations),
        tuple(origins),
    )


def input_facts(case: str) -> InputFacts:
    """Model-visible facts only; no oracle, family or gate is read."""
    raw = cast(dict[str, dict[str, object]], read("inputs-s2.json")["cases"])[case]
    return parse_facts(raw)


def declared_paths(facts: InputFacts) -> frozenset[str]:
    """Exact repository paths an application-known declaration makes visible."""
    return frozenset(
        x.request.path.value for x in facts.expectations if x.request.path is not None
    )


def manifest(facts: InputFacts, evidence: RepositoryEvidence) -> EvidenceManifest:
    if {f.path for f in evidence.files} != set(facts.selected_paths):
        raise ValueError("selected evidence mismatch")
    return EvidenceManifest(facts.question, evidence, PROVENANCE, facts.expectations)
