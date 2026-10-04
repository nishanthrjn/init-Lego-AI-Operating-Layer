"""Held-out freeze, accounting, safety and reproduction contracts."""

import ast
import json
from collections import Counter
from dataclasses import replace
from typing import cast

import pytest
from discovery2a.baseline import METHODS, Selection, accepted, select
from discovery2a.fixtures import load as originals
from discovery2a_holdout.data import (
    DIFFICULTIES,
    HERE,
    STRATA,
    Case,
    load,
    read,
    validate_case,
)
from discovery2a_holdout.evaluate import render, report, verify_freeze
from discovery2a_holdout.metrics import Row, correction, fold, measure, p90
from legoai_engineering.repository.workspace import WorkspaceEntryKind

CASES = load()


def test_frozen_condition() -> None:
    verify_freeze()
    assert read("preregistration-v1.json")["methods"] == list(METHODS)
    thresholds = read("thresholds-v1.json")
    assert thresholds["required_recall_min"] == 0.9
    assert thresholds["false_sufficient_max"] == 0
    assert thresholds["manual_ratio_max"] == 0.75


def test_schema_and_manifest() -> None:
    assert len(CASES) == 36
    assert {c.stratum for c in CASES} == STRATA
    assert min(Counter(c.stratum for c in CASES).values()) >= 2
    assert Counter(c.difficulty for c in CASES) == {
        "EASY": 3,
        "MEDIUM": 12,
        "HARD": 12,
        "PATH_ONLY_UNDERDETERMINED": 9,
    }
    for c in CASES:
        validate_case(c)
        assert len(c.fixture.structure().model_bytes()) <= 16384
    for task in cast(list[dict[str, object]], read("manifest-v1.json")["tasks"]):
        assert task["steps"] == [
            "objective",
            "tree",
            "ground_truth",
            "difficulty",
            "freeze",
            "selector_execution_after_all_freezes",
        ]


def test_non_reuse() -> None:
    old = originals()
    old_paths = {p for f in old for p in f.files}
    old_sets = {a for f in old for a in f.truth.acceptable}
    for case in CASES:
        f = case.fixture
        assert not set(f.files) & old_paths
        assert f.objective not in {o.objective for o in old}
        assert frozenset(f.files) not in {frozenset(o.files) for o in old}
        assert not set(f.truth.acceptable) & old_sets
    assert len({c.fixture.objective for c in CASES}) == 36
    assert len({frozenset(c.fixture.files) for c in CASES}) == 36


def test_ground_truth() -> None:
    c = CASES[0]
    for bad in (
        replace(c, difficulty="unknown"),
        replace(c, information_gap="content"),
        replace(
            c,
            fixture=replace(
                c.fixture,
                truth=replace(
                    c.fixture.truth, required=frozenset({"commerce/missing.py"})
                ),
            ),
        ),
        replace(
            c,
            fixture=replace(
                c.fixture, truth=replace(c.fixture.truth, forbidden=frozenset())
            ),
        ),
    ):
        with pytest.raises(ValueError):
            validate_case(bad)


@pytest.mark.parametrize("method", METHODS)
@pytest.mark.parametrize("case", CASES, ids=lambda c: c.fixture.id)
def test_deterministic_security(case: Case, method: str) -> None:
    f = case.fixture
    structure = f.structure()
    r = select(f.objective, structure, method)
    assert r == select(f.objective, structure, method)
    assert accepted(r, structure) and len(r.candidates) <= 8
    files = {
        e.path.value for e in structure.entries if e.kind is WorkspaceEntryKind.FILE
    }
    assert set(r.candidates) <= files
    assert all(p.encode() not in structure.model_bytes() for p in f.truth.forbidden)
    row = measure(case, method, r)
    for key in (
        "forbidden_disclosure",
        "undisclosed_acceptance",
        "directory_acceptance",
        "over_bound_acceptance",
    ):
        assert row.counts[key] == 0


def test_adversarial_membership() -> None:
    c = CASES[18]  # Large admitted tree supplies >8 real files.
    f = c.fixture
    files = sorted(p for p in f.files if p not in f.truth.forbidden)
    for proposed in (
        ("publishing/invented.py",),
        (f.roots[0],),
        (next(iter(f.truth.forbidden)),),
        tuple(files[:9]),
    ):
        result = Selection("succeeded", proposed)
        assert not accepted(result, f.structure())
        row = measure(c, "lexical", result)
        assert row.counts["accepted"] == 0 and row.counts["invalid"] == 1
        assert row.counts["reject"] == 1


def test_correction_operations() -> None:
    c = CASES[2]
    target = sorted(c.fixture.truth.acceptable[0])
    surplus = sorted(c.fixture.truth.irrelevant)[0]
    _, ops = correction(c, Selection("succeeded", (target[0], surplus)), True)
    assert ops == dict(remove=1, add=1, reject=0, clarify=0, create=0)
    _, ops = correction(c, Selection("succeeded", (surplus,)), True)
    assert ops == dict(remove=0, add=2, reject=1, clarify=0, create=0)
    _, ops = correction(c, Selection("insufficient_evidence", (), ("no_signal",)), True)
    assert ops == dict(remove=0, add=2, reject=0, clarify=0, create=0)
    ambiguous = CASES[10]
    _, ops = correction(
        ambiguous, Selection("insufficient_evidence", (), ("clarify",)), True
    )
    assert ops == dict(remove=0, add=0, reject=0, clarify=1, create=0)
    _, ops = correction(
        ambiguous, Selection("succeeded", (ambiguous.fixture.files[0],)), True
    )
    assert ops == dict(remove=0, add=0, reject=1, clarify=1, create=0)


def test_minimal_alternatives() -> None:
    c = CASES[17]
    for target in c.fixture.truth.acceptable:
        chosen, ops = correction(c, Selection("succeeded", tuple(sorted(target))), True)
        assert chosen == target and sum(ops.values()) == 0
    # Union is not a coherent success and requires removing the other branch.
    union = frozenset().union(*c.fixture.truth.acceptable)
    chosen, ops = correction(c, Selection("succeeded", tuple(sorted(union))), True)
    assert chosen in c.fixture.truth.acceptable and ops["remove"] == 2
    assert (
        measure(c, "lexical", Selection("succeeded", tuple(sorted(union)))).counts[
            "exact"
        ]
        == 0
    )
    smaller = CASES[16]
    single_path = next(iter(smaller.fixture.truth.acceptable[1]))
    _, ops = correction(smaller, Selection("succeeded", (single_path,)), True)
    assert sum(ops.values()) == 0


def test_false_sufficient() -> None:
    c = CASES[2]
    targets = sorted(c.fixture.truth.required)
    row = measure(c, "lexical", Selection("succeeded", (targets[0],)))
    assert row.counts["false_sufficient_selection"] == 1
    assert row.counts["catastrophic"] == 0
    row = measure(
        c, "lexical", Selection("succeeded", (next(iter(c.fixture.truth.irrelevant)),))
    )
    assert row.counts["false_sufficient_selection"] == row.counts["catastrophic"] == 1
    row = measure(c, "lexical", Selection("insufficient_evidence", (), ("no_signal",)))
    assert row.counts["false_sufficient_selection"] == row.counts["catastrophic"] == 0
    row = measure(
        c,
        "lexical",
        Selection("succeeded", (*targets, next(iter(c.fixture.truth.irrelevant)))),
    )
    assert row.counts["false_sufficient_selection"] == 0 and row.counts["exact"] == 0


def test_p90() -> None:
    assert p90([]) is None
    assert p90([4]) == 4
    assert p90(list(range(1, 11))) == 9
    assert p90(list(reversed(range(1, 12)))) == 10


def test_create() -> None:
    for c in (CASES[12], CASES[13]):
        row = measure(
            c, "lexical", Selection("insufficient_evidence", (), ("no_signal",))
        )
        assert row.counts["create"] == 1 and row.counts["create_correct"] == 1
        assert row.counts["clarify"] == 0 and row.counts["exact"] == 0
        row = measure(c, "lexical", Selection("succeeded", (c.fixture.files[0],)))
        assert row.counts["create_correct"] == 0 and row.counts["reject"] == 1


def rows_from(value: dict[str, object]) -> tuple[Row, ...]:
    return tuple(Row(**r) for r in cast(list[dict[str, object]], value["records"]))  # type: ignore[arg-type]


def test_folding() -> None:
    value = report()
    rows = rows_from(value)
    for method in METHODS:
        part = tuple(r for r in rows if r.method == method)
        summary = fold(part)
        counts = cast(dict[str, int], summary["counts"])
        assert counts == {k: sum(r.counts[k] for r in part) for k in part[0].counts}
        subcounts = [
            cast(
                dict[str, int],
                fold(tuple(r for r in part if r.difficulty == d))["counts"],
            )
            for d in DIFFICULTIES
        ]
        assert counts == {k: sum(c[k] for c in subcounts) for k in counts}
        assert (
            sum(cast(dict[str, int], summary["candidate_distribution"]).values()) == 36
        )
        assert cast(dict[str, object], summary["actionable_burden"])["n"] == 27


def test_reproduction_rendering() -> None:
    value = report()
    assert value == report()
    assert value == read("results-v1.json")
    assert render(value) == (HERE / "results-v1.md").read_text(encoding="utf-8")
    assert len(cast(list[object], value["records"])) == 108


def test_privacy() -> None:
    value = report()
    payload = json.dumps(value) + render(value)
    for c in CASES:
        assert c.fixture.objective not in payload
        assert all(p not in payload for p in c.fixture.files)
    c = replace(
        CASES[0],
        fixture=replace(CASES[0].fixture, objective="SECRET_OBJECTIVE_SENTINEL"),
    )
    from dataclasses import asdict

    row = measure(
        c,
        "lexical",
        Selection("insufficient_evidence", (), ("SECRET_OUTPUT_SENTINEL",)),
    )
    assert "SECRET_" not in json.dumps(asdict(row))
    assert "C:\\" not in payload and '"objective"' not in payload


def test_architecture() -> None:
    allowed = {
        "hashlib",
        "json",
        "dataclasses",
        "pathlib",
        "typing",
        "math",
        "statistics",
        "discovery2a",
        "discovery2a_holdout",
        "legoai_engineering",
    }
    for path in HERE.glob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            if isinstance(node, ast.Import):
                assert all(a.name.split(".")[0] in allowed for a in node.names)
            if isinstance(node, ast.ImportFrom) and node.module:
                assert node.module.split(".")[0] in allowed
                if node.module.startswith("legoai_engineering"):
                    assert node.module == "legoai_engineering.repository.workspace"
    # Neither the original baseline nor production can depend on the holdout oracle.
    assert "holdout" not in (HERE.parent / "discovery2a/baseline.py").read_text()
