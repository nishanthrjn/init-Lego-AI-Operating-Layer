"""Frozen safety-condition artifacts: fixtures, model-visible inputs, oracle, gates.

Model-visible input facts are read from inputs-s1.json only. Nothing here passes
an oracle field, family, critical flag or gate into the manifest.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from analyst_design_eval2.data import Policy, policy
from analyst_design_eval2.inputs import InputFacts
from legoai_engineering.analyst.sufficiency import EvidenceManifest
from legoai_engineering.analyst.values import RepositoryEvidence

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-sufficiency-safety-eval/1"
REPORT = "forgeai-analyst-sufficiency-safety-report/1"
PROVENANCE = "sufficiency-safety-eval1-observation"
FREEZE_DIGEST = "f5bf7654a1e77a5e5b8aa9d47e09c2475890b88bb4d97e136bef961891e4a9ca"
HISTORICAL = ("d21", "d22")  # exposed revision-2 cases: non-gating only
CASE_COUNT = 22


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_text(encoding="utf-8-sig").encode()).hexdigest()


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8"))
    )


def freeze() -> dict[str, str]:
    """Verify every frozen artifact (data and scorer) against freeze-s1.json."""
    if digest(HERE / "freeze-s1.json") != FREEZE_DIGEST:
        raise ValueError("safety freeze manifest changed")
    manifest = read("freeze-s1.json")
    if manifest["condition"] != CONDITION:
        raise ValueError("wrong safety condition")
    pins = cast(dict[str, str], manifest["artifacts"])
    for name, value in pins.items():
        if digest(HERE / name) != value:
            raise ValueError("frozen safety artifact changed: " + name)
    return pins


@dataclass(frozen=True)
class Case:
    id: str
    files: dict[str, str]


@dataclass(frozen=True)
class Oracle:
    id: str
    family: str
    pairs: tuple[str, ...]
    expected_disposition: str
    progression_allowed: bool
    critical: bool
    benign_control: bool
    reference_case: bool
    ambiguity_case: bool
    governing: tuple[str, ...]
    policy: Policy
    sensitive_paths: tuple[str, ...]
    edit_target_paths: tuple[str, ...]
    rationale: str


def _oracle(raw: dict[str, object]) -> Oracle:
    return Oracle(
        str(raw["id"]),
        str(raw["family"]),
        tuple(cast(list[str], raw["pairs"])),
        str(raw["expected_disposition"]),
        bool(raw["progression_allowed"]),
        bool(raw["critical"]),
        bool(raw["benign_control"]),
        bool(raw["reference_case"]),
        bool(raw["ambiguity_case"]),
        tuple(cast(list[str], raw["governing"])),
        policy(cast(dict[str, object], raw["request_policy"])),
        tuple(cast(list[str], raw["sensitive_paths"])),
        tuple(cast(list[str], raw["edit_target_paths"])),
        str(raw["rationale"]),
    )


def gates() -> dict[str, object]:
    return read("gates-s1.json")


def load() -> tuple[tuple[Case, Oracle], ...]:
    freeze()
    fixtures = cast(list[dict[str, object]], read("fixtures-s1.json")["cases"])
    oracles = cast(list[dict[str, object]], read("oracle-s1.json")["cases"])
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


def input_facts(case: str) -> InputFacts:
    """Model-visible facts only; no oracle, family or gate is read."""
    raw = cast(dict[str, dict[str, object]], read("inputs-s1.json")["cases"])[case]
    if set(raw) != {
        "question",
        "selected_paths",
        "expectations",
        "clarifications",
        "unknowns",
    }:
        raise ValueError("unexpected input facts")
    if raw["expectations"] or raw["clarifications"] or raw["unknowns"]:
        raise ValueError("safety condition declares no prerequisites")
    return InputFacts(
        str(raw["question"]), tuple(cast(list[str], raw["selected_paths"]))
    )


def manifest(facts: InputFacts, evidence: RepositoryEvidence) -> EvidenceManifest:
    if {f.path for f in evidence.files} != set(facts.selected_paths):
        raise ValueError("selected evidence mismatch")
    return EvidenceManifest(facts.question, evidence, PROVENANCE)
