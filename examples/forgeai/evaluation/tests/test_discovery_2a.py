"""DISCOVERY-2A requirements, independent metric examples and privacy checks."""

import ast
import hashlib
import json
from dataclasses import replace
from pathlib import Path
from typing import cast

import pytest
from discovery2a import evaluate as evaluation
from discovery2a.baseline import METHODS, Selection, accepted, select, tokens
from discovery2a.evaluate import COUNT_KEYS, evaluate, fold, measure, report
from discovery2a.fixtures import Fixture, load, validate
from legoai_engineering.repository.structure import StructureError

HERE = Path(__file__).resolve().parents[1] / "discovery2a"
FIXTURES = load()


def test_fixture_schema() -> None:
    # Canonical text hash survives Git's CRLF checkout conversion.
    content = (HERE / "fixtures-v1.json").read_text(encoding="utf-8")
    assert (
        hashlib.sha256(content.encode()).hexdigest()
        == "f3555d615363412b0bab8056182ac299bb48b5ddc46651c52e7a057a0610f8b2"
    )
    assert len(FIXTURES) == 17
    assert len({f.id for f in FIXTURES}) == 17
    for f in FIXTURES:
        validate(f)


def test_ground_truth_schema() -> None:
    f = FIXTURES[0]
    for truth in (
        replace(f.truth, required=frozenset({"src/absent.py"})),
        replace(f.truth, acceptable=(frozenset({"src/absent.py"}),)),
        replace(f.truth, irrelevant=frozenset()),
        replace(f.truth, forbidden=frozenset({"src/invoice.py"})),
        replace(f.truth, expected="insufficient_evidence"),
        replace(f.truth, manual_create=True),
    ):
        with pytest.raises(ValueError):
            validate(replace(f, truth=truth))


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("f", FIXTURES, ids=lambda f: f.id)
def test_determinism_membership_bound(f: Fixture, method: str) -> None:
    if f.truth.acquisition_blocked:
        with pytest.raises(StructureError):
            f.structure()
        assert evaluate(f, method).outcome == "acquisition_blocked"
        return
    structure = f.structure()
    result = select(f.objective, structure, method)
    assert result == select(f.objective, structure, method)
    assert accepted(result, structure)
    assert len(result.candidates) <= 8
    assert not set(result.candidates) & f.truth.forbidden
    assert all(p.encode() not in structure.model_bytes() for p in f.truth.forbidden)


@pytest.mark.parametrize(
    "candidate",
    [
        "src/unknown.py",
        "src/.env",
        "src",
        "src/Secrets/token.py",
        "../escape.py",
        "/absolute.py",
    ],
)
def test_unknown_forbidden_directory_rejected(candidate: str) -> None:
    f = FIXTURES[4]
    structure = f.structure()
    result = Selection("succeeded", (candidate,))
    assert not accepted(result, structure)
    row = measure(f, "lexical", result, structure)
    assert row.counts["invalid_proposals"] == 1
    assert row.counts["accepted_candidates"] == 0
    assert row.counts["unauthorized_acceptance"] == 0


def test_insufficient_semantics() -> None:
    s = FIXTURES[0].structure()
    assert not accepted(Selection("insufficient_evidence", ()), s)
    assert not accepted(Selection("succeeded", ()), s)
    assert not accepted(Selection("arbitrary", ()), s)
    assert not accepted(Selection("insufficient_evidence", (), ("",)), s)
    assert accepted(Selection("insufficient_evidence", (), ("needs_clarification",)), s)
    for method in METHODS:
        assert evaluate(FIXTURES[16], method).counts["insufficient_correct"] == 1


def test_create() -> None:
    f = FIXTURES[7]
    for method in METHODS:
        r = select(f.objective, f.structure(), method)
        assert r.status == "insufficient_evidence" and r.candidates == ()
        assert evaluate(f, method).counts["manual_create"] == 1
    assert not accepted(Selection("succeeded", ("src/recovery.py",)), f.structure())


def test_metric_derivation() -> None:
    f = FIXTURES[2]
    r = measure(
        f,
        "lexical",
        Selection("succeeded", ("src/invoice.py", "src/mail.py")),
        f.structure(),
    )
    c = r.counts
    assert c["true_positive"] == 1 and c["accepted_candidates"] == 2
    assert c["target_paths"] == 3 and c["required_hits"] == 1
    assert c["removed"] == 1 and c["added"] == 2
    assert c["irrelevant_paths"] == 1 and c["exact"] == 0
    assert c["correction_operations"] == 3 and c["correction_runs"] == 1
    a = fold((r,))
    assert a["candidate_precision"] == 1 / 2
    assert a["candidate_recall"] == 1 / 3
    assert a["required_path_recall"] == 1 / 3
    empty = measure(
        f,
        "lexical",
        Selection("insufficient_evidence", (), ("no_signal",)),
        f.structure(),
    )
    assert fold((empty,))["candidate_precision"] is None
    assert fold((empty,))["candidate_recall"] == 0
    assert empty.counts["clarification"] == 1
    assert empty.counts["insufficient_expected"] == 0


def test_multiple_acceptable_sets() -> None:
    f = FIXTURES[15]
    for alternative in f.truth.acceptable:
        r = measure(
            f, "lexical", Selection("succeeded", tuple(alternative)), f.structure()
        )
        assert r.counts["exact"] == 1 and r.counts["removed"] == 0
    union = tuple(sorted(frozenset().union(*f.truth.acceptable)))
    r = measure(f, "lexical", Selection("succeeded", union), f.structure())
    assert r.counts["exact"] == 0 and r.counts["removed"] == 1
    assert r.counts["true_positive"] == 1  # never reward the alternatives' union


def test_tie_top_k_and_unicode() -> None:
    f = replace(
        FIXTURES[0], files=tuple(f"src/cache_{i:02}.py" for i in reversed(range(12)))
    )
    for method in METHODS[:2]:
        r = select("cache", f.structure(), method)
        assert r.candidates == tuple(f"src/cache_{i:02}.py" for i in range(8))
    assert (
        select("cache", f.structure(), "conservative").status == "insufficient_evidence"
    )
    assert tokens("CAFÉ café Cafe\u0301") == frozenset({"café"})
    assert tokens("resetPassword") == frozenset({"reset", "password"})
    assert not accepted(Selection("succeeded", tuple(f.files[:9])), f.structure())
    assert not accepted(Selection("succeeded", (f.files[0], f.files[0])), f.structure())


def test_aggregate_fold() -> None:
    for method in METHODS:
        rows = tuple(evaluate(f, method) for f in FIXTURES)
        totals = fold(rows)["counts"]
        assert totals == {k: sum(r.counts[k] for r in rows) for k in COUNT_KEYS}
        for r in rows:
            assert set(r.counts) == set(COUNT_KEYS)
            assert all(n >= 0 for n in r.counts.values())
        assert (
            sum(
                cast(
                    dict[str, int], fold(rows)["candidate_count_distribution"]
                ).values()
            )
            == 15
        )


def test_privacy(monkeypatch: pytest.MonkeyPatch) -> None:
    sentinel = "CONFIDENTIAL_OBJECTIVE_CONTENT_SENTINEL"
    path_sentinel = "src/CONFIDENTIAL_PATH_SENTINEL.py"
    f = replace(
        FIXTURES[0],
        objective=sentinel,
        files=(path_sentinel,),
        truth=replace(
            FIXTURES[0].truth,
            required=frozenset({path_sentinel}),
            acceptable=(frozenset({path_sentinel}),),
            irrelevant=frozenset(),
        ),
    )
    validate(f)
    monkeypatch.setattr(evaluation, "load", lambda: (f,))
    payload = json.dumps(report())
    assert sentinel not in payload
    for name in f.files:
        assert name not in payload
    assert "src/" not in payload and "C:\\" not in payload
    assert '"candidates"' not in payload and '"objective"' not in payload


def test_frozen_report() -> None:
    assert report() == json.loads(
        (HERE / "results-v1.json").read_text(encoding="utf-8")
    )


def test_evaluation_boundary() -> None:
    allowed = {
        "json",
        "dataclasses",
        "pathlib",
        "typing",
        "re",
        "unicodedata",
        "discovery2a",
        "legoai_engineering",
    }
    for path in HERE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] in allowed for a in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] in allowed
                if node.module.startswith("legoai_engineering"):
                    assert node.module in {
                        "legoai_engineering.repository.structure",
                        "legoai_engineering.repository.workspace",
                    }
    baseline = (HERE / "baseline.py").read_text(encoding="utf-8-sig")
    assert "fixtures" not in baseline and "Truth" not in baseline
