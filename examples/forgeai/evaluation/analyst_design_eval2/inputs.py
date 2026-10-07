"""Pure initial manifest boundary: no oracle, fixture repository map or scorer."""

import json
from dataclasses import dataclass
from typing import cast

from legoai_engineering.analyst.sufficiency import (
    EvidenceManifest,
    GoverningSourceExpectation,
)
from legoai_engineering.analyst.values import RepositoryEvidence


@dataclass(frozen=True)
class InputFacts:
    question: str
    selected_paths: tuple[str, ...]
    expectations: tuple[GoverningSourceExpectation, ...] = ()
    expectation_provenance: tuple[str, ...] = ()
    unknowns: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if len(self.expectations) != len(self.expectation_provenance):
            raise ValueError("declaration provenance missing")
        if any(
            p
            not in {
                "application_known_prerequisite",
                "operator_provided_fact",
                "fixture_observable_fact",
            }
            for p in self.expectation_provenance
        ):
            raise ValueError("oracle declaration forbidden")


def initial_manifest(
    facts: InputFacts, evidence: RepositoryEvidence
) -> EvidenceManifest:
    if type(facts) is not InputFacts or type(evidence) is not RepositoryEvidence:
        raise TypeError("visible input facts and authorized evidence required")
    if {f.path for f in evidence.files} != set(facts.selected_paths):
        raise ValueError("selected evidence mismatch")
    return EvidenceManifest(
        facts.question,
        evidence,
        "design-eval2-observation",
        facts.expectations,
        (),
        facts.unknowns,
    )


def expected_payload(
    facts: InputFacts, evidence: RepositoryEvidence
) -> dict[str, object]:
    m = initial_manifest(facts, evidence)
    return {
        "question": m.question,
        "files": [{"path": f.path, "text": f.text} for f in m.evidence.files],
        "expectations": [
            {
                "key": x.key,
                "request": {
                    "kind": x.request.kind.value,
                    "description": x.request.description,
                    "path": x.request.path.value if x.request.path else None,
                    "choices": list(x.request.choices),
                },
                "supplied_paths": sorted(p.value for p in x.supplied_paths),
            }
            for x in sorted(m.expectations, key=lambda x: x.key)
        ],
        "clarifications": [],
        "unknowns": sorted(m.unknowns),
    }


def check_payload(
    facts: InputFacts, evidence: RepositoryEvidence, payload: str
) -> None:
    observed = cast(dict[str, object], json.loads(payload))
    if observed != expected_payload(facts, evidence):
        raise ValueError("model input differs from authorized visible facts")
