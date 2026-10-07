"""Frozen revision-3 artifacts: a sealed, independently authored safety condition.

Model-visible facts come from inputs-t3.json only. The oracle (families,
pairs, variants, critical flags, role concepts, intent groups, hidden governing
sources, rationale) and the gates are evaluator-only and never reach a manifest.
"""

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from analyst_design_eval2.inputs import InputFacts
from analyst_sufficiency_safety_eval1.data import Case
from analyst_sufficiency_safety_eval2.data import declared_paths, parse_facts
from legoai_engineering.analyst.sufficiency import EvidenceManifest
from legoai_engineering.analyst.values import RepositoryEvidence

HERE = Path(__file__).resolve().parent
CONDITION = "forgeai-analyst-sufficiency-safety-eval/3"
REPORT = "forgeai-analyst-sufficiency-safety-report/3"
PROVENANCE = "sufficiency-safety-eval3-observation"
FREEZE_DIGEST = "63d0d8546e9d0c129f66c8a1a188142be5129f2539cbde15368b77642ba7f0b8"
CASE_COUNT = 34
VARIANTS = ("attack", "twin", "standalone")
__all__ = [
    "CONDITION",
    "Case",
    "Criterion",
    "Intent",
    "Oracle",
    "Policy",
    "declared_paths",
    "freeze",
    "gates",
    "input_facts",
    "load",
    "manifest",
]


def digest(path: Path) -> str:
    """Line-ending-normalized SHA-256 (stable across checkouts)."""
    return hashlib.sha256(
        path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()
    ).hexdigest()


def read(name: str) -> dict[str, object]:
    return cast(
        dict[str, object], json.loads((HERE / name).read_text(encoding="utf-8"))
    )


def freeze() -> dict[str, str]:
    """Verify every frozen revision-3 artifact against freeze-t3.json."""
    if digest(HERE / "freeze-t3.json") != FREEZE_DIGEST:
        raise ValueError("safety freeze manifest changed")
    manifest = read("freeze-t3.json")
    if manifest["condition"] != CONDITION:
        raise ValueError("wrong safety condition")
    pins = cast(dict[str, str], manifest["artifacts"])
    for name, value in pins.items():
        if digest(HERE / name) != value:
            raise ValueError("frozen safety artifact changed: " + name)
    # Frozen code this condition reuses (the revision-2 path-establishment rule).
    for name, value in cast(dict[str, str], manifest["dependencies"]).items():
        if digest(HERE.parent / name) != value:
            raise ValueError("frozen safety dependency changed: " + name)
    return pins


@dataclass(frozen=True)
class Intent:
    id: str
    label: str  # evaluator-only canonical wording, used by scripted replies only
    tokens: frozenset[str]


@dataclass(frozen=True)
class Criterion:
    id: str
    kind: str
    path: str | None = None
    concept: tuple[frozenset[str], ...] = ()  # source_role facets (all must hit)
    label: str = ""
    intents: tuple[Intent, ...] = ()  # operator_clarification intent groups


@dataclass(frozen=True)
class Policy:
    required: tuple[Criterion, ...]
    allowed: tuple[Criterion, ...]
    forbidden_paths: tuple[str, ...]


@dataclass(frozen=True)
class Oracle:
    id: str
    family: str
    pair: str | None
    variant: str
    expected_disposition: str
    progression_allowed: bool
    critical: bool
    benign_control: bool
    reference_case: bool
    ambiguity_case: bool
    source_role_case: bool
    governing: tuple[str, ...]
    policy: Policy
    sensitive_paths: tuple[str, ...]
    edit_target_paths: tuple[str, ...]
    rationale: str


def _criterion(raw: dict[str, object]) -> Criterion:
    kind = str(raw["kind"])
    if kind not in {"named_evidence", "source_role", "operator_clarification"}:
        raise ValueError("unknown request kind")
    concept = tuple(
        frozenset(str(t) for t in facet)
        for facet in cast(list[list[str]], raw.get("concept", []))
    )
    intents = tuple(
        Intent(str(i["id"]), str(i["label"]), frozenset(cast(list[str], i["tokens"])))
        for i in cast(list[dict[str, object]], raw.get("intents", []))
    )
    if (kind == "named_evidence") != (raw["path"] is not None):
        raise ValueError("named criteria require a path; others forbid one")
    if (kind == "source_role") != bool(concept):
        raise ValueError("source_role criteria require a role concept")
    if (kind == "operator_clarification") != (len(intents) >= 2):
        raise ValueError("clarification criteria require two or more intents")
    return Criterion(
        str(raw["id"]),
        kind,
        cast(str | None, raw["path"]),
        concept,
        str(raw.get("label", "")),
        intents,
    )


def _oracle(raw: dict[str, object]) -> Oracle:
    p = cast(dict[str, object], raw["request_policy"])
    variant = str(raw["variant"])
    if variant not in VARIANTS:
        raise ValueError("unknown variant")
    return Oracle(
        str(raw["id"]),
        str(raw["family"]),
        cast(str | None, raw["pair"]),
        variant,
        str(raw["expected_disposition"]),
        bool(raw["progression_allowed"]),
        bool(raw["critical"]),
        bool(raw["benign_control"]),
        bool(raw["reference_case"]),
        bool(raw["ambiguity_case"]),
        bool(raw["source_role_case"]),
        tuple(cast(list[str], raw["governing"])),
        Policy(
            tuple(_criterion(c) for c in cast(list[dict[str, object]], p["required"])),
            tuple(_criterion(c) for c in cast(list[dict[str, object]], p["allowed"])),
            tuple(cast(list[str], p["forbidden_paths"])),
        ),
        tuple(cast(list[str], raw["sensitive_paths"])),
        tuple(cast(list[str], raw["edit_target_paths"])),
        str(raw["rationale"]),
    )


def gates() -> dict[str, object]:
    return read("gates-t3.json")


def load() -> tuple[tuple[Case, Oracle], ...]:
    freeze()
    fixtures = cast(list[dict[str, object]], read("fixtures-t3.json")["cases"])
    oracles = cast(list[dict[str, object]], read("oracle-t3.json")["cases"])
    result = []
    for f, o in zip(fixtures, oracles, strict=True):
        case = Case(str(f["id"]), dict(cast(dict[str, str], f["files"])))
        oracle = _oracle(o)
        if case.id != oracle.id:
            raise ValueError("case/oracle mismatch")
        result.append((case, oracle))
    ids = [c.id for c, _ in result]
    limits = gates()
    if (
        len(ids) != CASE_COUNT
        or len(set(ids)) != CASE_COUNT
        or ids != list(cast(list[str], limits["gating_cases"]))
        or [c.id for c, o in result if o.critical]
        != list(cast(list[str], limits["critical_cases"]))
    ):
        raise ValueError("safety case membership")
    pairs: dict[str, list[str]] = {}
    for _, oracle_ in result:
        if (oracle_.pair is None) != (oracle_.variant == "standalone"):
            raise ValueError("pair/variant mismatch")
        if oracle_.pair is not None:
            pairs.setdefault(oracle_.pair, []).append(oracle_.variant)
    if any(sorted(v) != ["attack", "twin"] for v in pairs.values()) or sorted(
        pairs
    ) != list(cast(list[str], limits["pairs"])):
        raise ValueError("every pair needs exactly one attack and one benign twin")
    return tuple(result)


def input_facts(case: str) -> InputFacts:
    """Model-visible facts only; no oracle, family or gate is read."""
    raw = cast(dict[str, dict[str, object]], read("inputs-t3.json")["cases"])[case]
    return parse_facts(raw)


def manifest(facts: InputFacts, evidence: RepositoryEvidence) -> EvidenceManifest:
    if {f.path for f in evidence.files} != set(facts.selected_paths):
        raise ValueError("selected evidence mismatch")
    return EvidenceManifest(facts.question, evidence, PROVENANCE, facts.expectations)
