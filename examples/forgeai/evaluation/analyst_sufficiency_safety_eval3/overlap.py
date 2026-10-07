"""Procedural independence check against earlier safety material.

Compares revision 3 with SAFETY-EVAL-1, SAFETY-EVAL-2 and the historical d21/d22
cases. It checks case ids, file paths, questions, hidden governing paths,
identical non-trivial lines, and shared six-word runs.

This is procedural independence (no reuse), not statistical independence.
Taxonomy labels and request-kind vocabulary are not compared.
"""

import json
import re
from pathlib import Path
from typing import Any, cast

HERE = Path(__file__).resolve().parent
EVALUATION = HERE.parent
SHINGLE = 6
LINE = 25  # characters; shorter lines (imports of stdlib, "return x") are generic
PRIOR = {
    "safety-eval-1": (
        "analyst_sufficiency_safety_eval1/fixtures-s1.json",
        "analyst_sufficiency_safety_eval1/inputs-s1.json",
        "analyst_sufficiency_safety_eval1/oracle-s1.json",
    ),
    "safety-eval-2": (
        "analyst_sufficiency_safety_eval2/fixtures-s2.json",
        "analyst_sufficiency_safety_eval2/inputs-s2.json",
        "analyst_sufficiency_safety_eval2/oracle-s2.json",
    ),
}
HISTORICAL = ("analyst_design_eval2/fixtures-v2.json", ("d21", "d22"))


def _read(name: str) -> Any:
    return json.loads((EVALUATION / name).read_text(encoding="utf-8"))


def _material(
    fixtures: list[dict[str, Any]],
    questions: list[str],
    governing: list[str],
) -> dict[str, Any]:
    texts = [t for f in fixtures for t in f["files"].values()]
    return {
        "ids": {f["id"] for f in fixtures},
        "paths": {p for f in fixtures for p in f["files"]},
        "questions": set(questions),
        "governing": set(governing),
        "texts": [*texts, *questions],
    }


def prior() -> dict[str, Any]:
    fixtures: list[dict[str, Any]] = []
    questions: list[str] = []
    governing: list[str] = []
    for fixture, inputs, oracle in PRIOR.values():
        fixtures += _read(fixture)["cases"]
        questions += [c["question"] for c in _read(inputs)["cases"].values()]
        governing += [p for o in _read(oracle)["cases"] for p in o["governing"]]
    name, ids = HISTORICAL
    for case in _read(name)["cases"]:
        if case["id"] in ids:
            fixtures.append(case)
            questions += [case["question"], case.get("revised_question", "")]
    return _material(fixtures, [q for q in questions if q], governing)


def current() -> dict[str, Any]:
    fixtures = json.loads((HERE / "fixtures-t3.json").read_text(encoding="utf-8"))
    inputs = json.loads((HERE / "inputs-t3.json").read_text(encoding="utf-8"))
    oracle = json.loads((HERE / "oracle-t3.json").read_text(encoding="utf-8"))
    return _material(
        fixtures["cases"],
        [c["question"] for c in inputs["cases"].values()],
        [p for o in oracle["cases"] for p in o["governing"]],
    )


def shingles(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.casefold())
    return {" ".join(words[i : i + SHINGLE]) for i in range(len(words) - SHINGLE + 1)}


def lines(text: str) -> set[str]:
    return {x.strip() for x in text.splitlines() if len(x.strip()) >= LINE}


def compare(new: dict[str, Any], old: dict[str, Any]) -> dict[str, list[str]]:
    def union(f: Any, texts: list[str]) -> set[str]:
        return cast(set[str], set().union(*(f(t) for t in texts)))

    return {
        "shared_ids": sorted(new["ids"] & old["ids"]),
        "shared_paths": sorted(new["paths"] & old["paths"]),
        "shared_questions": sorted(new["questions"] & old["questions"]),
        "shared_hidden_answers": sorted(new["governing"] & old["governing"]),
        "shared_lines": sorted(union(lines, new["texts"]) & union(lines, old["texts"])),
        "shared_shingles": sorted(
            union(shingles, new["texts"]) & union(shingles, old["texts"])
        ),
    }


def record() -> dict[str, object]:
    findings = compare(current(), prior())
    return {
        "method": "procedural: no reuse of ids, paths, questions, hidden governing "
        f"paths, identical lines of {LINE}+ characters or {SHINGLE}-word runs",
        "sources": sorted(
            [*(n for files in PRIOR.values() for n in files), HISTORICAL[0]]
        ),
        "historical_cases": list(HISTORICAL[1]),
        "shingle_words": SHINGLE,
        "line_characters": LINE,
        **findings,
        "independent": not any(findings.values()),
    }
