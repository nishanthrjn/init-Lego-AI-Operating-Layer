"""LQ1.2 reply classification: taxonomy, every category, and runtime agreement.

The agreement tests run each reply through the real ForgeAI flow (replay,
fake check sandboxes) and require the observed category to match the expected
one while ForgeAI's own verdict agrees; the classifier never decides alone.
"""

import json
from dataclasses import asdict
from pathlib import Path

import pytest
from diag_support import (
    SENTINEL,
    coding_samples,
    create_samples,
    observed_settings,
    part,
    review_samples,
    targets_of,
)
from eval_support import REVIEW_ACCEPT, fixture, reference
from legoai_engineering.repository.mutation import FileChangeKind, digest_text

from forgeai_eval.diagnostics import run_diagnostics
from forgeai_eval.outputs import (
    CodingDiagnostic,
    ReviewDiagnostic,
    classify_coding,
    classify_review,
)
from forgeai_eval.runner import evaluate_run

RECONCILIATION_ONLY = {
    "model_failure",
    "observation_unavailable",
    "classifier_disagreement",
}
SHAPES = {"object", "array", "string", "number", "boolean", "null", "none"}
CODING = coding_samples()
CREATE = create_samples()
REVIEW = review_samples()


def _synthetic(path_values: tuple[str, ...]) -> tuple[str, dict[str, object]]:
    digest = digest_text("a")
    reply = json.dumps(
        {
            "summary": "s",
            "changes": [
                {"path": p, "operation": "update", "content": "b", "reason": "r"}
                for p in path_values
            ],
            "risks": [],
            "unknowns": [],
        }
    )
    return reply, {p: (FileChangeKind.UPDATE, digest) for p in path_values}


def test_taxonomy_is_closed_and_every_parser_category_is_exercised() -> None:
    for enum in (CodingDiagnostic, ReviewDiagnostic):
        values = [member.value for member in enum]
        assert len(values) == len(set(values))
        assert all(v == v.lower() and " " not in v for v in values)
    exercised = {c.value for _, c in (*CODING.values(), *CREATE.values())}
    exercised |= {"changeset_invalid", "proposal_constraint_invalid"}  # synthetic
    assert exercised == {c.value for c in CodingDiagnostic} - RECONCILIATION_ONLY
    assert {c.value for _, c in REVIEW.values()} == (
        {c.value for c in ReviewDiagnostic} - RECONCILIATION_ONLY
    )


@pytest.mark.parametrize("case", sorted(CODING))
def test_coding_classification(case: str) -> None:
    reply, expected = CODING[case]
    diagnosis = classify_coding(reply, targets_of("stock-validation"))
    assert diagnosis.category == expected
    assert (diagnosis.fingerprint is not None) == (expected is CodingDiagnostic.VALID)


def test_create_and_synthetic_coding_classification() -> None:
    for reply, expected in CREATE.values():
        assert classify_coding(reply, targets_of("text-slug")).category == expected
    # Ancestor targets: rejected by RepositoryChangeSet, not as duplicates.
    reply, targets = _synthetic(("src", "src/a.py"))
    assert classify_coding(reply, targets).category == "changeset_invalid"  # type: ignore[arg-type]
    # A hidden path component is rejected only by CodingProposal (CodingTarget).
    reply, targets = _synthetic((".github/x.py",))
    assert classify_coding(reply, targets).category == "proposal_constraint_invalid"  # type: ignore[arg-type]


def test_fenced_json_remains_rejected_and_is_only_flagged() -> None:
    reply, _ = CODING["fenced-json"]
    diagnosis = classify_coding(reply, targets_of("stock-validation"))
    assert diagnosis.category == CodingDiagnostic.RESPONSE_NOT_JSON
    assert diagnosis.features.markdown_fence is True
    assert diagnosis.features.json_parse_succeeded is False
    plain = classify_coding(
        reference(fixture("stock-validation")), targets_of("stock-validation")
    )
    assert plain.features.markdown_fence is False


@pytest.mark.parametrize("case", sorted(REVIEW))
def test_review_classification(case: str) -> None:
    reply, expected = REVIEW[case]
    diagnosis = classify_review(reply)
    assert diagnosis.category == expected
    assert (diagnosis.fingerprint is not None) == (expected is ReviewDiagnostic.VALID)


def test_features_are_content_free() -> None:
    for reply, _ in CODING.values():
        diagnosis = classify_coding(reply, targets_of("stock-validation"))
        features = asdict(diagnosis.features)
        for name, value in features.items():
            if name == "top_level_type":
                assert value in SHAPES
            else:
                assert value is None or type(value) in {int, bool}, name
        assert SENTINEL not in repr(diagnosis)


def _run(
    tmp_path: Path, fixture_id: str, outputs: tuple[str, ...]
) -> dict[str, object]:
    settings, _ = observed_settings(tmp_path, outputs)
    return run_diagnostics(evaluate_run(fixture(fixture_id), 1, settings))


@pytest.mark.parametrize("case", sorted(CODING) + sorted(CREATE))
def test_coding_classifier_agrees_with_the_runtime(tmp_path: Path, case: str) -> None:
    fixture_id = "text-slug" if case in CREATE else "stock-validation"
    reply, expected = (CREATE | CODING)[case]
    diagnostics = _run(tmp_path, fixture_id, (reply, REVIEW_ACCEPT))
    (entry,) = part(diagnostics, "coding")
    assert entry["category"] == expected  # never classifier_disagreement
    succeeded = entry["output_status"] == "succeeded"
    assert succeeded == (expected is CodingDiagnostic.VALID)
    assert diagnostics["anomalies"] == {}


@pytest.mark.parametrize("case", sorted(REVIEW))
def test_review_classifier_agrees_with_the_runtime(tmp_path: Path, case: str) -> None:
    reply, expected = REVIEW[case]
    good = reference(fixture("stock-validation"))
    diagnostics = _run(tmp_path, "stock-validation", (good, reply))
    (entry,) = part(diagnostics, "review")
    assert entry["category"] == expected
    assert (entry["output_status"] == "completed") == (
        expected is ReviewDiagnostic.VALID
    )
